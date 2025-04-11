import streamlit as st
import time
import datetime
import uuid
import re
from difflib import SequenceMatcher
from database import save_knowledge, get_knowledge, search_knowledge
from openai_service import (
    process_knowledge, 
    generate_knowledge_tags, 
    generate_smart_questions,
    process_question_answers,
    correct_arabic_text  # إضافة وظيفة تصحيح النص العربي
)
from utils import get_sample_departments, format_relative_time, truncate_text

def are_questions_similar(question1, question2, threshold=0.7):
    """
    تحقق مما إذا كان سؤالان متشابهين جوهرياً باستخدام خوارزمية مقارنة السلاسل
    ومعالجة اللغة الطبيعية البسيطة
    
    Args:
        question1: السؤال الأول
        question2: السؤال الثاني
        threshold: عتبة التشابه (0.0 - 1.0)، حيث 1.0 هو التطابق الكامل
        
    Returns:
        Boolean: هل السؤالان متشابهان بدرجة كافية؟
    """
    # تنظيف الأسئلة من علامات الترقيم والكلمات غير المهمة
    def clean_question(text):
        # إزالة علامات الترقيم
        text = re.sub(r'[،,\.؟\?!]', ' ', text)
        # تحويل إلى أحرف صغيرة (للنصوص الإنجليزية)
        text = text.lower()
        # إزالة الكلمات غير المهمة في العربية
        stop_words = ['هل', 'ما', 'من', 'في', 'على', 'عن', 'إلى', 'هو', 'هي', 'أو', 'أن', 'التي', 'الذي']
        for word in stop_words:
            text = text.replace(f' {word} ', ' ')
        # إزالة المسافات المتعددة
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # تنظيف الأسئلة
    clean_q1 = clean_question(question1)
    clean_q2 = clean_question(question2)
    
    # استخدام خوارزمية مقارنة السلاسل لمعرفة درجة التشابه
    similarity_ratio = SequenceMatcher(None, clean_q1, clean_q2).ratio()
    
    # إذا كان هناك كلمات مشتركة مهمة، زيادة درجة التشابه
    # الكلمات المهمة في سياق نظام المعرفة
    important_words = ['كهرباء', 'كهربائي', 'حريق', 'إصابة', 'ضرر', 'مسؤول', 'صيانة', 'إبلاغ', 'تصليح', 
                     'مشكلة', 'تماس', 'عزل', 'تيار', 'معدة', 'آلة', 'جهاز', 'موقع', 'مكان', 'طابق', 'دور']
    
    # عدد الكلمات المهمة المشتركة
    common_important_words = sum(1 for word in important_words 
                               if word in clean_q1 and word in clean_q2)
    
    # زيادة درجة التشابه بناءً على الكلمات المهمة المشتركة
    if common_important_words > 0:
        # زيادة بنسبة 10% لكل كلمة مهمة مشتركة، بحد أقصى 30%
        similarity_ratio += min(0.3, common_important_words * 0.1)
    
    # إذا تجاوزت درجة التشابه العتبة المحددة، نعتبر السؤالين متشابهين
    return similarity_ratio >= threshold

def process_search_query(openai_client, db_client, query):
    """Process a search query from the user"""
    # Perform search
    with st.spinner("جاري البحث..."):
        try:
            # المسار 1: استخدام البحث الأساسي القائم على الكلمات المفتاحية
            # البحث في قاعدة البيانات مباشرة وهذا هو الأكثر موثوقية
            search_results = search_knowledge(db_client, query)
            print(f"Basic search found {len(search_results)} results")
            
            # Check if we have results
            if not search_results:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "لم أتمكن من العثور على أي معلومات تطابق استعلامك. يرجى تجربة مصطلحات بحث مختلفة أو إضافة المزيد من الكلمات المفتاحية.",
                    "timestamp": time.time()
                })
            else:
                # Format search results
                results_text = "إليك نتائج البحث:\n\n"
                for i, result in enumerate(search_results[:5]):  # Limit to top 5 results
                    # التعامل مع الطوابع الزمنية بطريقة آمنة
                    timestamp = result.get("timestamp", 0)
                    # التأكد من أن الطابع الزمني عدد صحيح
                    if isinstance(timestamp, (float, int)):
                        created_time = format_relative_time(int(timestamp))
                    else:
                        created_time = "وقت غير معروف"
                        
                    department = result.get('department', 'غير معروف')
                    employee = result.get('employee_name', 'غير معروف')
                    
                    results_text += f"**النتيجة {i+1}** - من قسم {department}\n"
                    results_text += f"تمت المشاركة بواسطة: {employee} ({created_time})\n"
                    results_text += f"{truncate_text(result.get('content', ''), 350)}\n\n"
                    
                    # Add separator between results except after the last one
                    if i < len(search_results[:5]) - 1:
                        results_text += "---\n\n"
                
                # Add search results to chat history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": results_text,
                    "timestamp": time.time()
                })
                
        except Exception as e:
            print(f"Error during search: {str(e)}")
            # ارجع رسالة أكثر تفصيلاً للمستخدم تساعد في فهم المشكلة
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "عذرًا، واجهنا مشكلة أثناء البحث. يبدو أن قاعدة البيانات لا تحتوي على معلومات كافية حول هذا الموضوع بعد. حاول مشاركة معرفة جديدة حول هذا الموضوع أولاً.",
                "timestamp": time.time()
            })

def start_knowledge_collection(openai_client, db_client, employee_name, department, knowledge_text):
    """Start the knowledge collection process with follow-up questions"""
    with st.spinner("جاري معالجة مشاركة المعرفة..."):
        try:
            # معالجة المعرفة الأولية
            processed_content = process_knowledge(openai_client, knowledge_text)
            
            # تهيئة مصفوفات لتخزين الأسئلة والأجوبة
            previous_questions = []
            previous_answers = []
            
            # لن نخزن الأسئلة مسبقاً، سنولد كل سؤال فقط عندما نحتاجه بناءً على السياق المتطور للمحادثة
            # توليد السؤال الأول فقط باستخدام OpenAI
            try:
                first_question_list = generate_smart_questions(openai_client, processed_content)
                # نأخذ فقط السؤال الأول، وسنولد الأسئلة التالية لاحقاً حسب سياق المحادثة
                first_question = first_question_list[0] if first_question_list else None
            except Exception as e:
                print(f"Error generating first question: {str(e)}")
                first_question = None
                
            # إذا فشل توليد السؤال، فسنستخدم نظام ذكي لتحليل المحتوى وتوليد سؤال مناسب
            if not first_question:
                import random
                
                # تحليل نوع المحتوى
                content_lower = processed_content.lower()
                
                # أنواع مختلفة من المحتوى والكلمات المفتاحية المرتبطة بها
                content_types = {
                    "كهرباء": ["كهرباء", "كهربائي", "تماس", "فولت", "أسلاك", "تيار"],
                    "حادث": ["حادث", "إصابة", "ضرر", "خطر", "إسعاف", "طوارئ"],
                    "منتج": ["منتج", "سلعة", "بضاعة", "مخزون", "قطعة", "صنف"],
                    "إجراء": ["إجراء", "عملية", "خطوات", "تعليمات", "دليل", "طريقة"],
                    "مكان": ["مكان", "موقع", "مبنى", "طابق", "مكتب", "قاعة", "دور"],
                    "شخص": ["موظف", "شخص", "مدير", "مسؤول", "عامل", "فريق"]
                }
                
                # تحديد نوع المحتوى
                detected_type = "عام"  # النوع الافتراضي
                max_matches = 0
                
                for content_type, keywords in content_types.items():
                    matches = sum(1 for word in keywords if word in content_lower)
                    if matches > max_matches:
                        max_matches = matches
                        detected_type = content_type
                
                # قائمة من الأسئلة المخصصة حسب نوع المحتوى
                questions_by_type = {
                    "كهرباء": [
                        "هل يمكنك تحديد المكان الدقيق للمشكلة الكهربائية وتأثيرها على المرافق الأخرى؟",
                        "هل تم إبلاغ مسؤول الصيانة عن هذه المشكلة، ومن هو المسؤول المعني؟",
                        "ما هي الإجراءات الوقائية أو التصحيحية التي يجب اتخاذها؟"
                    ],
                    "حادث": [
                        "هل نتج عن هذا الحادث أي إصابات أو أضرار، وما هي الخطوات التي تم اتخاذها؟",
                        "هل تم توثيق الحادث وإبلاغ الجهات المعنية؟",
                        "ما هي الإجراءات التي يمكن اتخاذها لمنع وقوع حوادث مماثلة مستقبلاً؟"
                    ],
                    "منتج": [
                        "هل يمكنك تقديم المزيد من التفاصيل الفنية أو المواصفات لهذا المنتج؟",
                        "ما هي تطبيقات واستخدامات هذا المنتج في المؤسسة؟",
                        "هل هناك بدائل أو إصدارات أخرى من هذا المنتج؟"
                    ],
                    "إجراء": [
                        "هل هناك أي متطلبات أو شروط مسبقة قبل البدء في هذا الإجراء؟",
                        "ما هي المدة المتوقعة والموارد اللازمة لإتمام هذا الإجراء؟",
                        "هل هناك أي تحديات أو مشاكل شائعة مرتبطة بهذا الإجراء؟"
                    ],
                    "مكان": [
                        "ما هي ساعات الوصول المسموحة وإجراءات الأمان لهذا المكان؟",
                        "هل هناك مرافق أو معدات خاصة متوفرة في هذا المكان؟",
                        "من هو المسؤول أو جهة الاتصال المعنية بهذا المكان؟"
                    ],
                    "شخص": [
                        "ما هي مسؤوليات وصلاحيات هذا الشخص في المؤسسة؟",
                        "ما هي معلومات الاتصال المباشرة وأفضل طريقة للتواصل؟",
                        "ما هي خبرات هذا الشخص وكيف يمكن الاستفادة منها؟"
                    ],
                    "عام": [
                        "هل يمكنك تقديم المزيد من التفاصيل أو المعلومات حول هذا الموضوع؟",
                        "هل هناك أي جهات اتصال أو موارد إضافية متعلقة بهذا الأمر؟",
                        "هل هناك معلومات أخرى مهمة يجب مشاركتها حول هذا الموضوع؟"
                    ]
                }
                
                # اختيار سؤال عشوائي من النوع المناسب
                first_question = random.choice(questions_by_type.get(detected_type, questions_by_type["عام"]))
            
            # تخزين المعرفة في حالة الجلسة
            # لا نخزن قائمة أسئلة محددة مسبقاً، سنولد كل سؤال في وقته
            st.session_state.current_knowledge = {
                "original_text": knowledge_text,
                "processed_text": processed_content,
                "question_index": 0,
                "questions": [first_question],  # نخزن فقط السؤال الأول
                "answers": [""],  # مكان للإجابة على السؤال الأول
                "complete": False,
                "previous_questions": previous_questions,  # لتخزين أسئلة المحادثة
                "previous_answers": previous_answers       # لتخزين إجابات المحادثة
            }
            
            # تعيين وضع المحادثة لجمع المعرفة
            st.session_state.conversation_mode = "knowledge_collection"
            
            # محاولة تحليل نوع المحتوى لإضافة تعليق مخصص
            content_type_detected = ""
            
            # تحليل المحتوى لإضافة تعليق شخصي
            content_lower = processed_content.lower()
            
            # كلمات مفتاحية للكشف عن أنواع المحتوى الشائعة
            if "كهرباء" in content_lower or "كهربائي" in content_lower or "تماس" in content_lower:
                content_type_detected = "أرى أن هذا يتعلق بمشكلة كهربائية. "
            elif "حريق" in content_lower or "دخان" in content_lower:
                content_type_detected = "شكراً على الإبلاغ عن هذا الحادث المتعلق بالسلامة. "
            elif "عطل" in content_lower or "صيانة" in content_lower:
                content_type_detected = "أفهم أن هناك مشكلة تحتاج للصيانة. "
            elif "دور" in content_lower or "طابق" in content_lower or "مكتب" in content_lower:
                content_type_detected = "أرى أن هذا يتعلق بموقع محدد في المبنى. "
            
            # تحسين الرسالة الترحيبية
            welcome_messages = [
                "شكراً على مشاركة هذه المعلومات القيمة! لجعلها أكثر فائدة للجميع، أود أن أسألك:",
                "هذه معلومات مهمة! لإثراء قاعدة المعرفة المؤسسية:",
                "شكراً جزيلاً! لتوثيق هذه المعلومات بشكل شامل ومفيد:"
            ]
            
            import random
            welcome_message = random.choice(welcome_messages)
            
            # إضافة رد المساعد مع السؤال الأول
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"{content_type_detected}{welcome_message}\n\n{first_question}",
                "timestamp": time.time()
            })
            
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة المعرفة: {str(e)}")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "آسف، حدث خطأ أثناء معالجة المعرفة. يرجى المحاولة مرة أخرى.",
                "timestamp": time.time()
            })
            # Reset to normal conversation mode
            st.session_state.conversation_mode = "normal"

def process_knowledge_collection(openai_client, db_client, employee_name, department, answer):
    """Process answer to a follow-up question during knowledge collection"""
    # حفظ الإجابة على السؤال الحالي
    current_idx = st.session_state.current_knowledge["question_index"]
    st.session_state.current_knowledge["answers"][current_idx] = answer
    
    # إضافة السؤال والجواب إلى سجل المحادثة
    current_question = st.session_state.current_knowledge["questions"][current_idx]
    st.session_state.current_knowledge["previous_questions"].append(current_question)
    st.session_state.current_knowledge["previous_answers"].append(answer)
    
    # زيادة مؤشر السؤال
    st.session_state.current_knowledge["question_index"] += 1
    
    # التحقق مما إذا كنا قد طرحنا 3 أسئلة (كحد أقصى)
    if st.session_state.current_knowledge["question_index"] >= 3:
        # لقد جمعنا كل الإجابات، معالجة المعرفة النهائية
        with st.spinner("جاري معالجة وحفظ المعرفة النهائية..."):
            try:
                # دمج المعرفة الأصلية مع الأسئلة والأجوبة
                final_knowledge = process_question_answers(
                    openai_client,
                    st.session_state.current_knowledge["processed_text"],
                    st.session_state.current_knowledge["previous_questions"],  # استخدام الأسئلة التي طرحنا بالفعل
                    st.session_state.current_knowledge["previous_answers"]     # استخدام الإجابات التي جمعنا
                )
                
                # توليد الكلمات المفتاحية
                tags = generate_knowledge_tags(openai_client, final_knowledge)
                
                # حفظ في قاعدة البيانات
                knowledge_id = save_knowledge(db_client, final_knowledge, department, employee_name)
                
                # وضع علامة على المعرفة على أنها مكتملة
                st.session_state.current_knowledge["complete"] = True
                
                # إنشاء رسالة المساعد بتنسيق أكثر تنظيماً
                completion_messages = [
                    "شكراً لمشاركة هذه المعلومات القيمة. لقد قمت بمعالجة ودمج جميع المعلومات في إدخال معرفة شامل:",
                    "رائع! لقد اكتملت المعرفة الآن. قمت بتنظيم ودمج المعلومات التي شاركتها في معرفة متكاملة:",
                    "ممتاز! اكتملت المعلومات الآن. قمت بمعالجتها وتنظيمها وتصحيحها لتصبح كما يلي:"
                ]
                
                import random
                completion_message = random.choice(completion_messages)
                
                assistant_message = f"{completion_message}\n\n{final_knowledge}\n\n**الكلمات المفتاحية:** {', '.join(tags)}"
                
                # إضافة إلى سجل المحادثة
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": assistant_message,
                    "timestamp": time.time(),
                    "is_knowledge_saved": True
                })
                
                # إعادة تعيين وضع المحادثة
                st.session_state.conversation_mode = "normal"
                
            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة المعرفة النهائية: {str(e)}")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "آسف، حدث خطأ أثناء معالجة المعرفة النهائية. يرجى المحاولة مرة أخرى.",
                    "timestamp": time.time()
                })
                # إعادة التعيين إلى وضع المحادثة العادي
                st.session_state.conversation_mode = "normal"
    else:
        # توليد السؤال التالي بناءً على سياق المحادثة الحالي
        with st.spinner("جاري توليد سؤال المتابعة..."):
            try:
                # توليد سؤال جديد بناء على المعرفة الأصلية وسجل المحادثة السابق
                next_questions = generate_smart_questions(
                    openai_client, 
                    st.session_state.current_knowledge["processed_text"],
                    st.session_state.current_knowledge["previous_questions"],
                    st.session_state.current_knowledge["previous_answers"]
                )
                
                # استخدام السؤال الأول من القائمة المرجعة
                next_question = next_questions[0] if next_questions else "هل هناك أي معلومات إضافية مهمة تود مشاركتها؟"
                
                # تخزين السؤال الجديد في قائمة الأسئلة
                st.session_state.current_knowledge["questions"].append(next_question)
                st.session_state.current_knowledge["answers"].append("")  # إضافة مساحة فارغة للإجابة القادمة
                
                # إضافة نص تشجيعي قبل السؤال التالي
                question_prefix = "شكراً على هذه المعلومات المفيدة! لدي سؤال آخر لاستكمال المعرفة:"
                
                # إضافة رد المساعد مع السؤال التالي
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"{question_prefix}\n\n{next_question}",
                    "timestamp": time.time()
                })
                
            except Exception as e:
                st.error(f"حدث خطأ أثناء توليد السؤال التالي: {str(e)}")
                
                # في حالة الفشل مع OpenAI، استخدم DummyAI لتوليد سؤال مناسب
                # الذي سيعتمد على نوع المحتوى إذا أمكن
                
                # تحليل سياق المحادثة (المعرفة + الأسئلة السابقة + الإجابات)
                content_context = st.session_state.current_knowledge["processed_text"]
                previous_qa = []
                for q, a in zip(st.session_state.current_knowledge["previous_questions"], 
                               st.session_state.current_knowledge["previous_answers"]):
                    previous_qa.append(f"س: {q}")
                    previous_qa.append(f"ج: {a}")
                
                full_context = content_context + "\n\n" + "\n".join(previous_qa)
                
                # استخدام خوارزمية بسيطة لتحليل السياق وتوليد سؤال مناسب
                general_questions = [
                    "هل هناك أي إجراءات أو خطوات محددة يجب اتباعها في هذه الحالة؟",
                    "ما هي الإجراءات الوقائية التي يمكن اتخاذها لتجنب تكرار هذه المشكلة؟",
                    "هل هناك آثار جانبية أو تأثيرات على أقسام أو مناطق أخرى؟",
                    "هل هناك مسؤول أو فريق محدد يجب التواصل معه في مثل هذه الحالات؟",
                    "هل هناك أي معلومات إضافية مهمة تؤثر على فهم أو التعامل مع هذا الموضوع؟"
                ]
                
                import random
                fallback_question = random.choice(general_questions)
                
                # محاولة تخصيص السؤال حسب نوع المحتوى والسؤال السابق
                # قاموس من الأسئلة المتخصصة حسب نوع المحتوى
                specialized_questions = {
                    "كهربائي": [
                        "هل تم عزل التيار الكهربائي عن المنطقة المتضررة؟",
                        "هل تم تحديد مصدر المشكلة الكهربائية؟",
                        "هل هناك أي إصابات أو أضرار نتجت عن هذه المشكلة؟",
                        "هل تم إبلاغ مسؤول الصيانة أو قسم السلامة بالمشكلة؟",
                        "ما هي الخطوات الوقائية التي ستتخذ لمنع تكرار هذه المشكلة مستقبلاً؟",
                        "هل هناك أجزاء أخرى من المبنى متأثرة بهذه المشكلة الكهربائية؟"
                    ],
                    "حريق": [
                        "هل تم تفعيل نظام إنذار الحريق؟",
                        "هل تم إخلاء المبنى وفقاً لإجراءات السلامة؟",
                        "ما هو سبب الحريق المحتمل؟",
                        "هل تم الاتصال بالدفاع المدني؟",
                        "هل هناك أي إصابات أو خسائر بشرية؟",
                        "هل تم تقييم الأضرار المادية الناتجة عن الحريق؟"
                    ],
                    "عطل": [
                        "متى بدأ هذا العطل في الظهور؟",
                        "هل تمت محاولة إصلاح العطل من قبل؟",
                        "هل العطل يؤثر على سير العمل اليومي؟",
                        "هل هناك بدائل متاحة أثناء إصلاح العطل؟",
                        "من هو المسؤول عن متابعة إصلاح هذا العطل؟",
                        "ما هي القطع أو المواد المطلوبة للإصلاح؟"
                    ],
                    "مكان": [
                        "ما هو الموقع الدقيق وكيفية الوصول إليه؟",
                        "هل هناك تصاريح خاصة أو متطلبات أمنية للوصول؟",
                        "ما هي المرافق المتوفرة في هذا المكان؟",
                        "كم عدد الأشخاص الذين يمكن أن يستوعبهم هذا المكان؟",
                        "هل هناك أوقات محددة للعمل أو الزيارة؟",
                        "من المسؤول عن هذا المكان وكيفية التواصل معه؟"
                    ],
                    "موظف": [
                        "ما هو دور هذا الموظف الرئيسي ومسؤولياته؟",
                        "ما هي قنوات التواصل المباشر مع هذا الموظف؟",
                        "ما هي ساعات عمل هذا الموظف أو مواعيد تواجده؟",
                        "هل هناك بديل لهذا الموظف في حالة عدم تواجده؟",
                        "هل يملك هذا الموظف صلاحيات خاصة أو خبرات محددة؟",
                        "ما هو القسم أو الإدارة التي يتبع لها هذا الموظف؟"
                    ]
                }
                
                # تحديد نوع المحتوى من السياق
                content_types = {
                    "كهربائي": ["كهرباء", "كهربائي", "تماس", "فولت", "أسلاك", "تيار"],
                    "حريق": ["حريق", "دخان", "حرارة", "لهب", "إطفاء", "طفاية"],
                    "عطل": ["عطل", "خلل", "صيانة", "إصلاح", "تصليح", "معطل", "توقف"],
                    "مكان": ["مكان", "غرفة", "مكتب", "طابق", "دور", "مبنى", "قاعة"],
                    "موظف": ["موظف", "مدير", "عامل", "مشرف", "مهندس", "فني", "مسؤول"]
                }
                
                # تحديد نوع المحتوى
                detected_type = None
                max_matches = 0
                
                for content_type, keywords in content_types.items():
                    matches = sum(1 for word in keywords if word in full_context.lower())
                    if matches > max_matches:
                        max_matches = matches
                        detected_type = content_type
                
                # إذا تم اكتشاف نوع محتوى واضح، استخدم الأسئلة المتخصصة المناسبة
                if detected_type and detected_type in specialized_questions:
                    # فلترة الأسئلة لتجنب تكرار ما سبق طرحه
                    previous_questions = st.session_state.current_knowledge["previous_questions"]
                    available_questions = [q for q in specialized_questions[detected_type] 
                                          if not any(are_questions_similar(q, prev_q) for prev_q in previous_questions)]
                    
                    # إذا كانت هناك أسئلة متبقية، اختر واحدًا عشوائيًا
                    if available_questions:
                        fallback_question = random.choice(available_questions)
                    else:
                        # إذا تم استخدام كل الأسئلة المتخصصة، استخدم أسئلة عامة
                        fallback_question = random.choice(general_questions)
                else:
                    # إذا لم يتم اكتشاف نوع محتوى واضح، استخدم سؤالًا عامًا
                    fallback_question = random.choice(general_questions)
                
                # تخزين السؤال وإضافة مساحة للإجابة
                st.session_state.current_knowledge["questions"].append(fallback_question)
                st.session_state.current_knowledge["answers"].append("")
                
                # إضافة رد المساعد مع السؤال المولد
                response_prefixes = [
                    "أفهم. لدي سؤال متابعة مهم: ",
                    "شكراً على هذه المعلومات. لاستكمال الصورة: ",
                    "هذا يساعدني على فهم الوضع بشكل أفضل. سؤالي التالي: "
                ]
                
                response_prefix = random.choice(response_prefixes)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"{response_prefix}{fallback_question}",
                    "timestamp": time.time()
                })

def show_chat_interface(openai_client, db_client):
    """Display the chat interface for knowledge sharing"""
    st.title("منصة إدارة المعرفة")
    
    # Initialize session states
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "conversation_mode" not in st.session_state:
        st.session_state.conversation_mode = "normal"  # normal, knowledge_collection, search
        
    if "current_knowledge" not in st.session_state:
        st.session_state.current_knowledge = {
            "original_text": "",
            "processed_text": "",
            "question_index": 0,  # Current question index (0-2)
            "questions": [],      # List of smart questions
            "answers": [],        # List of answers to questions
            "previous_questions": [],  # سجل الأسئلة السابقة للمحادثة الحالية
            "previous_answers": [],    # سجل الإجابات السابقة للمحادثة الحالية
            "complete": False     # Whether knowledge collection is complete
        }
    
    # Get user information in sidebar
    with st.sidebar:
        st.header("معلومات المستخدم")
        employee_name = st.text_input("الاسم:", key="employee_name")
        department = st.selectbox(
            "القسم:", 
            options=get_sample_departments(),
            key="user_department"
        )
        
        st.markdown("---")
        
        # Mode selection
        st.subheader("وضع المحادثة")
        if st.button("مشاركة معرفة جديدة", use_container_width=True):
            # Reset the conversation mode to normal to start fresh
            st.session_state.conversation_mode = "normal"
            st.rerun()
            
        if st.button("البحث في قاعدة المعرفة", use_container_width=True):
            # Set to search mode
            st.session_state.conversation_mode = "search"
            
            # Add system message to indicate search mode
            if not any(msg.get("is_search_mode", False) for msg in st.session_state.chat_history):
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "أنا هنا للمساعدة في البحث عن المعلومات في قاعدة المعرفة. ما الذي تبحث عنه؟",
                    "timestamp": time.time(),
                    "is_search_mode": True
                })
            st.rerun()
        
        # Clear chat history button
        if st.button("مسح المحادثة", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.conversation_mode = "normal"
            st.session_state.current_knowledge = {
                "original_text": "",
                "processed_text": "",
                "question_index": 0,
                "questions": [],
                "answers": [],
                "previous_questions": [],  # إعادة ضبط سجل الأسئلة
                "previous_answers": [],    # إعادة ضبط سجل الإجابات
                "complete": False
            }
            st.rerun()
    
    # Main chat area
    chat_container = st.container()
    
    with chat_container:
        # Style for the chat messages
        st.markdown("""
        <style>
        .user-message {
            background-color: #e9f5ff;
            padding: 10px 15px;
            border-radius: 15px;
            margin: 5px 0;
            text-align: right;
            direction: rtl;
        }
        .assistant-message {
            background-color: #f0f0f0;
            padding: 10px 15px;
            border-radius: 15px;
            margin: 5px 0;
            direction: rtl;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # عرض سجل المحادثة مع تنسيق الرسائل
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                # عرض رسالة المستخدم مع نص مصحح
                st.markdown(f"<div class='user-message'>{message['content']}</div>", unsafe_allow_html=True)
                
                # إظهار النص الأصلي في حالة وجود تصحيحات جوهرية
                if message.get("original_text") and message.get("original_text") != message['content']:
                    # تحديد الاختلافات الجوهرية (أكثر من حروف علة أو ترقيم)
                    if len(set(message.get("original_text")).symmetric_difference(set(message['content']))) > 3:
                        with st.expander("عرض النص الأصلي"):
                            st.text(message.get("original_text"))
            else:
                # عرض رسالة المساعد
                st.markdown(f"<div class='assistant-message'>{message['content']}</div>", unsafe_allow_html=True)
                
                # عرض مؤشر نجاح حفظ المعرفة
                if message.get("is_knowledge_saved", False):
                    st.success("✅ تم حفظ المعرفة بنجاح!")
    
    # Input area at bottom
    st.write("---")
    
    # User input field
    user_input = st.text_area(
        "اكتب رسالتك هنا:",
        height=100,
        key="user_message"
    )
    
    # Send button
    if st.button("إرسال", use_container_width=True, key="send_message"):
        if not user_input.strip():
            st.error("الرجاء كتابة رسالة أولاً.")
            return
        
        if not employee_name.strip():
            st.error("الرجاء إدخال اسمك في الشريط الجانبي.")
            return
        
        # تصحيح الأخطاء الإملائية في رسالة المستخدم
        corrected_input = correct_arabic_text(user_input)
        
        # إضافة رسالة المستخدم إلى سجل المحادثة (مع التصحيح)
        st.session_state.chat_history.append({
            "role": "user",
            "content": corrected_input,  # استخدم النص المصحح
            "original_text": user_input,  # احتفظ بالنص الأصلي للمرجعية
            "timestamp": time.time()
        })
        
        # معالجة الرسالة بناءً على وضع المحادثة (استخدام النص المصحح)
        if st.session_state.conversation_mode == "search":
            # معالجة استعلام البحث باستخدام النص المصحح
            process_search_query(openai_client, db_client, corrected_input)
            
        elif st.session_state.conversation_mode == "knowledge_collection":
            # نحن في منتصف عملية جمع المعرفة مع أسئلة المتابعة
            process_knowledge_collection(openai_client, db_client, employee_name, department, corrected_input)
            
        else:  # الوضع العادي - افتراض أن هذه معرفة جديدة للمشاركة
            # بدء عملية جمع المعرفة
            start_knowledge_collection(openai_client, db_client, employee_name, department, corrected_input)
            
        # إذا كان النص المصحح مختلفًا عن النص الأصلي، أظهر ملاحظة للمستخدم
        if corrected_input != user_input:
            st.info("👨‍💻 تم تصحيح بعض الأخطاء الإملائية في المدخلات.")
        
        # Rerun to update the UI
        st.rerun()
