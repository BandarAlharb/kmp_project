import os
import json
import re
from openai import OpenAI

class DummyClient:
    """A dummy client class for when the OpenAI API is not available"""
    def __init__(self, error_message="OpenAI API key is not set or invalid. Using fallback mode."):
        self.error_message = error_message
        
    def __getattr__(self, name):
        # Return a method that raises an exception when called
        def method(*args, **kwargs):
            raise ValueError(self.error_message)
        return method

def initialize_openai_client():
    """Initialize OpenAI client with API key"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY environment variable not set")
        # Use a dummy client that will trigger fallbacks later
        return DummyClient("OpenAI API key is not set. Please provide a valid API key.")
    
    try:
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # Do not change this unless explicitly requested by the user
        client = OpenAI(api_key=api_key)
        
        # Test the connection with a simple request
        test_response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use simpler model for test
            messages=[
                {"role": "user", "content": "test"}
            ],
            max_tokens=5
        )
        
        print("OpenAI API connection successful")
        return client
        
    except Exception as e:
        print(f"Error initializing OpenAI client: {str(e)}")
        # Use a dummy client that will trigger fallbacks
        return DummyClient(f"Error with OpenAI API: {str(e)}. Using fallback mode.")

def process_knowledge(client, text, format_type="markdown"):
    """Process and enhance knowledge text using OpenAI API"""
    system_prompt = (
        "You are an AI assistant helping a knowledge management platform. "
        "Your task is to process knowledge contributions from employees, "
        "enhance them for clarity, and structure them professionally. "
        "Maintain all factual information and technical accuracy while improving:"
        "\n- Structure and organization"
        "\n- Clarity and conciseness"
        "\n- Grammar and professional language"
        "\n- Add relevant section headings if appropriate"
    )
    
    user_prompt = f"Please process and enhance the following knowledge contribution:\n\n{text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # The newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=2000
        )
        
        enhanced_text = response.choices[0].message.content
        return enhanced_text
    
    except Exception as e:
        # Log error but try to improve the text even without API access
        print(f"Error processing knowledge with OpenAI: {str(e)}")
        
        # Apply some basic enhancements even without the API
        processed_text = text.strip()
        
        # Try to fix common typographical errors in Arabic
        corrections = {
            "هنان": "هناك",
            "هناك،": "هناك",
            "الى": "إلى",
            "فى": "في",
            "منتة": "منتج"
        }
        
        for wrong, correct in corrections.items():
            processed_text = processed_text.replace(wrong, correct)
        
        # Add a title if it doesn't seem to have one
        lines = processed_text.split('\n')
        if len(lines) == 1 or len(lines[0]) > 50:  # No title or first line too long
            title = processed_text.split('.')[0]
            if len(title) > 50:
                title = title[:50] + "..."
            processed_text = f"## {title.strip()}\n\n{processed_text}"
            
        # Return the lightly processed text
        return processed_text

def generate_knowledge_tags(client, text):
    """Generate relevant tags for knowledge content"""
    system_prompt = (
        "You are a knowledge management AI that helps categorize information. "
        "Extract 3-5 relevant tags from the text provided. "
        "Return only the tags as a JSON array of strings."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # The newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        result = json.loads(response.choices[0].message.content)
        if isinstance(result, dict) and "tags" in result:
            return result["tags"]
        elif isinstance(result, list):
            return result
        else:
            # Try to find tags in the response
            return result.get("tags", [])
            
    except Exception as e:
        print(f"Error generating tags: {str(e)}")
        
        # Try to generate tags from text analysis without API
        tags = []
        text_lower = text.lower()
        
        # Simple keyword detection based on common themes/domains
        keywords = {
            "مورد": ["موردين", "مزودين", "مشتريات", "توريد"],
            "ورد": ["زهور", "نباتات", "تنسيق زهور"],
            "توصيل": ["خدمة توصيل", "توصيل سريع", "شحن"],
            "منتج": ["منتجات", "سلع", "بضائع"],
            "إجراء": ["عملية", "خطوات", "سياسة", "إجراءات"],
            "خدمة": ["خدمات", "دعم", "مساعدة"],
            "معلومات": ["بيانات", "معرفة"],
            "جديد": ["جديد", "حديث", "تحديث"]
        }
        
        # Look for each keyword in the text
        for base_word, related_tags in keywords.items():
            if base_word in text_lower:
                tags.append(base_word)
                # Add a related tag if we have fewer than 3 tags
                for tag in related_tags:
                    if len(tags) < 5 and tag not in tags:
                        tags.append(tag)
                        break
        
        # If we have product-specific text, add domain-specific tags
        if "ورد" in text_lower or "زهور" in text_lower or "نبات" in text_lower:
            for flower_tag in ["ورد", "زهور", "تنسيق", "هدايا"]:
                if flower_tag not in tags and len(tags) < 5:
                    tags.append(flower_tag)
        
        # Ensure we have at least one tag
        if not tags:
            tags.append("معلومات عامة")
            
        return tags

def generate_smart_questions(client, knowledge_text, previous_questions=None, previous_answers=None):
    """
    Generate smart follow-up questions to complete the knowledge
    
    Args:
        client: OpenAI client
        knowledge_text: The original knowledge text
        previous_questions: List of questions already asked
        previous_answers: List of answers already received
    """
    # تنسيق systemPrompt محسّن باستخدام إرشادات أكثر وضوحاً ومعلومات حول تخصيص الأسئلة
    system_prompt = (
        "أنت مساعد ذكي داخل منصة إدارة معرفة، هدفك هو التحاور بشكل طبيعي مع الموظفين لجمع معلومات مهمة "
        "حول الموضوع المطروح. يجب أن يكون سؤالك التالي:\n"
        "1. طبيعياً وتلقائياً (كأنه محادثة عادية بين شخصين) وليس استجواباً رسمياً\n"
        "2. مختلفاً تماماً عن الأسئلة السابقة (تجنب أي تكرار)\n"
        "3. محدداً وموجهاً بناءً على النص ونوع المعلومات المطروحة (مثلاً: مشكلة كهربائية، منتج، موظف، إلخ)\n"
        "4. مركّزاً على استخراج تفاصيل حاسمة وضرورية غير موجودة في النص الأصلي\n"
        "5. مخصصاً بشكل ذكي لنوع المعلومات (استخدام أسئلة مناسبة: للحوادث - أسئلة الأمان والتقارير، للمنتجات - أسئلة المواصفات، إلخ)\n\n"
        "يجب أن تتوقع عن أي نوع من المعلومات نتحدث وتطرح سؤالاً ذكياً واحداً فقط مناسباً تماماً للسياق والمرحلة.\n"
        "إذا كانت المعلومات عن حادثة/مشكلة، ركز على: المخاطر، الإجراءات المتخذة، الوقت، الحل، التبليغ.\n"
        "إذا كانت المعلومات عن منتج/خدمة، ركز على: المواصفات، الاستخدام، التكلفة، الإتاحة، البدائل.\n"
        "إذا كانت المعلومات عن إجراء، ركز على: الخطوات، المتطلبات، المسؤولين، الفترة الزمنية، الشروط.\n"
        "إذا كانت المعلومات عن شخص/جهة، ركز على: بيانات الاتصال، الدور، المسؤوليات، الخبرات.\n"
        "أظهر أنك تفهم ما قاله المستخدم من خلال تخصيص السؤال والمقدمة بناءً على ما ذكره بالفعل."
    )
    
    # بناء سياق المحادثة الكامل للنموذج بشكل أكثر طبيعية
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"المستخدم شارك المعلومات التالية: {knowledge_text}"}
    ]
    
    # إضافة الأسئلة والإجابات السابقة كمحادثة طبيعية
    if previous_questions and previous_answers:
        for q, a in zip(previous_questions, previous_answers):
            if q and a:  # نتأكد من أن السؤال والإجابة غير فارغين
                conversation.append({"role": "assistant", "content": q})
                conversation.append({"role": "user", "content": a})
    
    # طلب توليد سؤال ذكي مناسب
    final_prompt = (
        "بناءً على المحادثة السابقة، ما هو السؤال الأكثر ملاءمة والذي ستطرحه الآن للحصول على معلومات "
        "قيّمة وضرورية غير متوفرة بعد؟ السؤال يجب أن يكون طبيعياً ومخصصاً لنوع المعلومات المطروحة. "
        "اهتم بإظهار تفهمك لما ذكره المستخدم من خلال طريقة صياغة السؤال. قدم سؤالاً واحداً فقط."
    )
    conversation.append({"role": "user", "content": final_prompt})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # The newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=conversation,
            temperature=0.7  # درجة حرارة متوسطة لتوليد محادثة طبيعية مع توجيه مناسب
        )
        
        # استخراج السؤال من رد API
        next_question = response.choices[0].message.content
        
        # إزالة أي علامات اقتباس أو تنسيق زائد قد يظهر في السؤال
        next_question = next_question.strip('"\'').strip()
        
        # نرجع قائمة تحتوي على سؤال واحد فقط
        return [next_question]
        
    except Exception as e:
        print(f"Error generating smart questions: {str(e)}")
        
        # Intelligent fallback - analyze text to create better questions even when API fails
        knowledge_text_lower = knowledge_text.lower()
        
        # بالكلمات المفتاحية المتعلقة بالسيارات بالعربية والإنجليزية
        car_keywords = ["سيارة", "مركبة", "car", "vehicle", "سيارات", "شاحنة", "تويوتا", "مرسيدس", "هوندا", 
                     "نيسان", "مازدا", "نقل", "بضائع", "ركاب", "toyota", "honda", "nissan", "mercedes", 
                     "موديل", "model", "بيك اب", "pickup", "لون", "color", "white", "بيضاء", "سوداء", "black"]
        
        # كلمات مفتاحية للموردين
        supplier_keywords = ["مورد", "مزود", "بائع", "supplier", "vendor", "موزع", "distributor", "محل", "متجر",
                         "store", "shop", "سوق", "market", "شركة", "company", "تاجر", "تجار"]
        
        # كلمات مفتاحية للمنتجات
        product_keywords = ["منتج", "سلعة", "product", "item", "بضاعة", "goods", "merchandise", "صنف", "أصناف",
                        "مقاس", "size", "وزن", "weight", "نوعية", "quality", "ماركة", "brand"]
        
        # كلمات مفتاحية للإجراءات
        process_keywords = ["إجراء", "عملية", "خطوات", "process", "procedure", "steps", "protocol", "طريقة", 
                        "method", "نظام", "system", "آلية", "mechanism"]
        
        # كلمات مفتاحية للمعدات
        equipment_keywords = ["معدة", "آلة", "جهاز", "equipment", "machine", "device", "tool", "أداة", "أدوات",
                          "tools", "machinery", "ماكينة"]
                          
        # كلمات مفتاحية للأماكن
        location_keywords = ["مكان", "موقع", "مقر", "location", "place", "office", "مكتب", "فرع", "branch", 
                         "مستودع", "warehouse", "مخزن", "storage", "عنوان", "address"]
                         
        # كلمات مفتاحية للبرامج والأنظمة
        software_keywords = ["برنامج", "نظام", "تطبيق", "software", "system", "app", "application", "موقع", 
                         "website", "platform", "منصة"]
                         
        # كلمات مفتاحية للأشخاص وجهات الاتصال
        person_keywords = ["شخص", "مسؤول", "موظف", "contact", "person", "employee", "مدير", "manager", 
                       "director", "مشرف", "supervisor", "مختص", "specialist"]
                       
        # التحقق من نوع المحتوى عن طريق الكلمات المفتاحية الأكثر تكراراً
        keyword_groups = [
            (car_keywords, "car"),
            (supplier_keywords, "supplier"),
            (product_keywords, "product"),
            (process_keywords, "process"),
            (equipment_keywords, "equipment"),
            (location_keywords, "location"),
            (software_keywords, "software"),
            (person_keywords, "person")
        ]
        
        # حساب عدد الكلمات المفتاحية لكل فئة
        category_scores = {}
        for keywords, category in keyword_groups:
            score = 0
            for keyword in keywords:
                if keyword in knowledge_text_lower:
                    score += 1
                    # أهمية أكبر للكلمات المفتاحية الدقيقة الطويلة
                    if len(keyword) > 4:
                        score += 1
            category_scores[category] = score
            
        # تحديد الفئة ذات الدرجة الأعلى
        max_score = 0
        top_category = "default"
        for category, score in category_scores.items():
            if score > max_score:
                max_score = score
                top_category = category
        
        # Check category and return appropriate questions
        
        # السيارات والمركبات
        if top_category == "car" or any(word in knowledge_text_lower for word in car_keywords):
            # تحديد إذا كانت هناك معلومات عن سيارة للبيع أو للاستخدام التجاري
            is_commercial = any(word in knowledge_text_lower for word in ["نقل", "بضائع", "تجاري", "commercial", "cargo", "delivery"])
            is_for_sale = any(word in knowledge_text_lower for word in ["بيع", "شراء", "sale", "سعر", "price", "تكلفة", "cost"])
            
            if is_commercial:
                return [
                    "ما هي الحالة الفنية للسيارة وعدد الكيلومترات المقطوعة؟",
                    "ما هي الحمولة القصوى (بالكيلوجرام) التي تستطيع السيارة نقلها؟",
                    "هل هناك رقم تواصل مع مالك السيارة أو المسؤول عنها؟"
                ]
            elif is_for_sale:
                return [
                    "ما هو سعر السيارة والطريقة المفضلة للدفع؟",
                    "ما هي حالة السيارة الفنية وتاريخ صيانتها؟",
                    "هل هناك رقم تواصل مع البائع وموعد متاح لمعاينة السيارة؟"
                ]
            else:
                return [
                    "ما هي المواصفات الدقيقة للسيارة (المحرك، السعة، إلخ)؟",
                    "هل يمكنك تقديم معلومات الاتصال بمالك السيارة؟",
                    "هل هناك أي مشاكل فنية أو صيانة مطلوبة للسيارة حالياً؟"
                ]
        
        # الموردين والموزعين 
        elif top_category == "supplier" or any(word in knowledge_text_lower for word in supplier_keywords):
            return [
                "ما هي معلومات الاتصال بهذا المورد؟ (رقم الهاتف، البريد الإلكتروني، العنوان)",
                "ما هي أوقات العمل وهل يقدم خدمة التوصيل؟",
                "ما هي أبرز المنتجات أو الخدمات التي يقدمها هذا المورد وهل هناك حد أدنى للطلب؟"
            ]
        
        # الإجراءات والعمليات
        elif top_category == "process" or any(word in knowledge_text_lower for word in process_keywords):
            return [
                "ما هي الخطوات التفصيلية لهذا الإجراء بترتيب التنفيذ؟",
                "هل هناك متطلبات أو شروط مسبقة يجب توفرها قبل تنفيذ هذا الإجراء؟",
                "هل هناك تحديات أو مشاكل شائعة قد تواجه الموظفين أثناء تنفيذ هذا الإجراء وكيفية التعامل معها؟"
            ]
        
        # المنتجات
        elif top_category == "product" or any(word in knowledge_text_lower for word in product_keywords):
            return [
                "ما هي المواصفات الكاملة لهذا المنتج (الأبعاد، الوزن، المميزات)؟",
                "ما هي استخدامات هذا المنتج الرئيسية والفرعية؟",
                "ما هو سعر المنتج وهل هناك بدائل له في حال عدم توفره؟"
            ]
            
        # المعدات والآلات
        elif top_category == "equipment" or any(word in knowledge_text_lower for word in equipment_keywords):
            return [
                "ما هي المواصفات الفنية التفصيلية لهذه المعدة ومتطلبات تشغيلها؟",
                "كيف يمكن صيانة هذه المعدة وما هي قطع الغيار الأكثر استهلاكاً؟",
                "هل هناك تدريب خاص مطلوب لاستخدام هذه المعدة ومن هو الشخص المسؤول عنها؟"
            ]
            
        # الأماكن والمواقع
        elif top_category == "location" or any(word in knowledge_text_lower for word in location_keywords):
            return [
                "ما هو العنوان الدقيق لهذا المكان وأقرب معلم بارز له؟",
                "ما هي ساعات العمل الرسمية وهل يوجد مواقف سيارات قريبة؟",
                "هل هناك رقم اتصال أو شخص مسؤول يمكن التواصل معه قبل الزيارة؟"
            ]
            
        # البرامج والأنظمة
        elif top_category == "software" or any(word in knowledge_text_lower for word in software_keywords):
            return [
                "ما هي متطلبات النظام اللازمة لتشغيل هذا البرنامج وإجراءات التثبيت؟",
                "هل هناك دليل استخدام أو فيديوهات تدريبية متاحة للموظفين الجدد؟",
                "من هو المسؤول عن الدعم الفني لهذا البرنامج وكيفية التواصل معه عند وجود مشكلة؟"
            ]
            
        # الأشخاص وجهات الاتصال
        elif top_category == "person" or any(word in knowledge_text_lower for word in person_keywords):
            return [
                "ما هي معلومات الاتصال المباشرة بهذا الشخص (هاتف، بريد إلكتروني، واتساب)؟",
                "ما هو دور ومسؤوليات هذا الشخص تحديداً وفي أي قسم يعمل؟",
                "ما هي أوقات الدوام لهذا الشخص والطريقة المفضلة للتواصل معه؟"
            ]
        
        # أسئلة افتراضية محسنة في حالة عدم تحديد نوع المحتوى
        return [
            "ما هي التفاصيل الإضافية المهمة التي يجب معرفتها عن هذا الموضوع؟",
            "هل هناك جهة اتصال أو شخص محدد يمكن الرجوع إليه للمزيد من المعلومات؟",
            "هل هناك أي معلومات مهمة أخرى تود إضافتها لتكتمل الفائدة؟"
        ]

def process_question_answers(client, knowledge_text, questions, answers):
    """Process the original knowledge and question-answers into a comprehensive knowledge entry"""
    system_prompt = (
        "You are a knowledge management assistant. You have received an original knowledge contribution "
        "along with follow-up questions and answers. Your task is to integrate all this information "
        "into a comprehensive, well-structured knowledge entry. Maintain factual accuracy while improving:"
        "\n- Structure and organization"
        "\n- Completeness of information"
        "\n- Clarity and professional language"
        "\n- Add appropriate section headings"
        "\nMake sure the final result reads as a cohesive document, not as a Q&A format."
    )
    
    # Format the questions and answers for the prompt
    qa_formatted = ""
    for i, (question, answer) in enumerate(zip(questions, answers)):
        qa_formatted += f"\n\nQuestion {i+1}: {question}\nAnswer {i+1}: {answer}"
    
    user_prompt = f"Please integrate this original knowledge contribution and the follow-up Q&A into a comprehensive knowledge entry:\n\nOriginal contribution:\n{knowledge_text}\n{qa_formatted}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # The newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2500
        )
        
        integrated_knowledge = response.choices[0].message.content
        return integrated_knowledge
    
    except Exception as e:
        print(f"Error processing question answers: {str(e)}")
        
        # Create a more structured document without API assistance
        # Start with a better title
        title = knowledge_text.split('\n')[0].strip()
        if not title.startswith('#'):
            if len(title) > 50:  # If first line is too long, extract a reasonable title
                title = title.split('.')[0][:50] + "..."
            title = f"# {title}\n\n"
        else:
            title = f"{title}\n\n"
        
        # Identify content type based on keywords
        knowledge_text_lower = knowledge_text.lower()
        
        # Check for different content types
        is_car = any(word in knowledge_text_lower for word in ["سيارة", "مركبة", "car", "vehicle", "سيارات", "شاحنة"])
        is_supplier = any(word in knowledge_text_lower for word in ["مورد", "supplier", "vendor", "بائع", "مزود"])
        is_product = any(word in knowledge_text_lower for word in ["منتج", "product", "بضاعة", "سلعة"])
        is_process = any(word in knowledge_text_lower for word in ["إجراء", "عملية", "خطوات", "process", "procedure", "steps"])
        is_software = any(word in knowledge_text_lower for word in ["برنامج", "نظام", "تطبيق", "software", "system", "app"])
        is_equipment = any(word in knowledge_text_lower for word in ["معدة", "آلة", "جهاز", "equipment", "machine"])
        is_location = any(word in knowledge_text_lower for word in ["مكان", "موقع", "مقر", "location", "place", "office"])
        is_person = any(word in knowledge_text_lower for word in ["شخص", "مسؤول", "موظف", "contact", "person", "employee"])
        
        structured_content = title
        
        # Add original knowledge as main body
        structured_content += f"{knowledge_text.strip()}\n\n"
        
        # Add appropriate section title based on content type
        if is_car:
            structured_content += "## معلومات السيارة\n\n"
        elif is_supplier:
            structured_content += "## معلومات المورد\n\n"
        elif is_product:
            structured_content += "## تفاصيل المنتج\n\n"
        elif is_process:
            structured_content += "## تفاصيل الإجراء\n\n"
        elif is_software:
            structured_content += "## معلومات البرنامج/النظام\n\n"
        elif is_equipment:
            structured_content += "## تفاصيل المعدة/الجهاز\n\n"
        elif is_location:
            structured_content += "## معلومات الموقع/المكان\n\n"
        elif is_person:
            structured_content += "## معلومات الشخص/جهة الاتصال\n\n"
        else:
            structured_content += "## معلومات إضافية\n\n"
        
        # Add question-answer pairs in a structured way
        for i, (question, answer) in enumerate(zip(questions, answers)):
            # If the answer is empty, skip this pair
            if not answer.strip():
                continue
                
            # For car information
            if is_car:
                if "حالة" in question or "تعمل" in question or "فنية" in question:
                    structured_content += f"### الحالة الفنية للسيارة\n{answer}\n\n"
                elif "اتصال" in question or "مالك" in question or "تواصل" in question:
                    structured_content += f"### معلومات المالك/الاتصال\n{answer}\n\n"
                elif "سعة" in question or "تحميل" in question or "قدرة" in question or "capacity" in question:
                    structured_content += f"### قدرة التحميل والسعة\n{answer}\n\n"
                else:
                    structured_content += f"### {question}\n{answer}\n\n"
                    
            # For supplier information
            elif is_supplier:
                if "اتصال" in question or "phone" in question.lower() or "contact" in question.lower():
                    structured_content += f"### معلومات الاتصال\n{answer}\n\n"
                elif "توصيل" in question or "delivery" in question.lower():
                    structured_content += f"### خدمة التوصيل\n{answer}\n\n"
                elif "منتجات" in question or "خدمات" in question or "products" in question.lower() or "services" in question.lower():
                    structured_content += f"### المنتجات والخدمات\n{answer}\n\n"
                else:
                    structured_content += f"### {question}\n{answer}\n\n"
                    
            # For product information
            elif is_product:
                if "مواصفات" in question or "specification" in question.lower():
                    structured_content += f"### المواصفات\n{answer}\n\n"
                elif "استخدام" in question or "usage" in question.lower() or "application" in question.lower():
                    structured_content += f"### الاستخدامات\n{answer}\n\n"
                elif "بدائل" in question or "alternative" in question.lower():
                    structured_content += f"### البدائل المتاحة\n{answer}\n\n"
                else:
                    structured_content += f"### {question}\n{answer}\n\n"
                    
            # For process information
            elif is_process:
                if "خطوات" in question or "steps" in question.lower():
                    structured_content += f"### الخطوات التفصيلية\n{answer}\n\n"
                elif "متطلبات" in question or "requirement" in question.lower() or "شروط" in question:
                    structured_content += f"### المتطلبات والشروط\n{answer}\n\n"
                elif "تحديات" in question or "مشاكل" in question or "challenge" in question.lower() or "issue" in question.lower():
                    structured_content += f"### التحديات والمشاكل المحتملة\n{answer}\n\n"
                else:
                    structured_content += f"### {question}\n{answer}\n\n"
            
            # For other content types
            else:
                # Try to create a meaningful section title based on the question
                if "اتصال" in question or "phone" in question.lower() or "contact" in question.lower():
                    structured_content += f"### معلومات الاتصال\n{answer}\n\n"
                elif "متطلبات" in question or "requirements" in question.lower():
                    structured_content += f"### المتطلبات\n{answer}\n\n"
                elif "مواصفات" in question or "specifications" in question.lower() or "features" in question.lower():
                    structured_content += f"### المواصفات والميزات\n{answer}\n\n"
                else:
                    # Use the question itself as section title if all else fails
                    structured_content += f"### {question}\n{answer}\n\n"
        
        # Add a conclusion if needed
        structured_content += "## ملاحظات ختامية\n"
        structured_content += "تم تجميع هذه المعلومات بواسطة نظام إدارة المعرفة. يرجى التحقق من دقة المعلومات قبل الاعتماد عليها بشكل كامل.\n"
        
        return structured_content

def correct_arabic_text(text):
    """
    تصحيح الأخطاء الإملائية الشائعة في اللغة العربية
    
    هذه الوظيفة تقوم بتصحيح الأخطاء الإملائية الشائعة مثل:
    - خسب -> خشب
    - الى -> إلى 
    - مفاوضه -> مفاوضة
    - وغيرها من الأخطاء الشائعة
    """
    # قائمة التصحيحات الإملائية الشائعة
    corrections = {
        # أخطاء الحروف المتشابهة
        "خسب": "خشب",
        "سجرة": "شجرة",
        "صندوك": "صندوق",
        "طاولط": "طاولة",
        "ضابط": "ضابط",
        "حهاز": "جهاز",
        "جهار": "جهاز",
        
        # أخطاء الهمزات
        "الى": "إلى",
        "انا": "أنا",
        "اسم": "اسم",
        "احمد": "أحمد",
        "اكثر": "أكثر",
        "اقل": "أقل",
        
        # أخطاء التاء المربوطة
        "مفاوضه": "مفاوضة",
        "شركه": "شركة",
        "معلومه": "معلومة",
        "بضاعه": "بضاعة",
        "سياره": "سيارة",
        "شاحنه": "شاحنة",
        
        # أخطاء حروف العلة
        "فى": "في",
        "الذى": "الذي",
        "على": "على",
        "الة": "آلة",
        
        # أخطاء شائعة أخرى
        "منتة": "منتج",
        "هنان": "هناك",
        "هناك،": "هناك",
        "انة": "أنه",
        "لاكن": "لكن",
        "عندة": "عنده",
        "عنده،": "عنده",
        "يومياً": "يومياً",
        "اخر": "آخر",
        "الاخر": "الآخر",
        "الان": "الآن",
        "حائز": "جاهز",
        
        # أخطاء ترقيم شائعة
        "،و": "، و",
        "،ف": "، ف",
        "؟و": "؟ و",
        "!و": "! و",
        
        # إضافة مسافة بعد علامات الترقيم
        "،": "، ",
        ".": ". ",
        "؛": "؛ ",
        ":": ": "
    }
    
    # تطبيق التصحيحات
    for wrong, correct in corrections.items():
        text = re.sub(r'\\b' + wrong + r'\\b', correct, text)
        text = text.replace(wrong, correct)  # استخدام الاستبدال المباشر كاحتياط إضافي
    
    # إرجاع النص المصحح
    return text

def search_knowledge_semantically(client, query, knowledge_items):
    """Perform semantic search on knowledge items using OpenAI embeddings"""
    if not knowledge_items:
        return []
    
    try:
        # Method 1: Try using OpenAI semantic search
        system_prompt = (
            "You are a knowledge management assistant helping with semantic search. "
            "Given a user query and a set of knowledge items, return the IDs of the "
            "most relevant items in order of relevance. Return response as a JSON array "
            "of IDs with at most 5 results."
        )
        
        # Format knowledge items for prompt
        formatted_items = []
        for item in knowledge_items:
            formatted_items.append(f"ID: {item['id']}\nContent: {item['content'][:500]}...")
        
        knowledge_corpus = "\n\n".join(formatted_items)
        
        user_prompt = f"Query: {query}\n\nKnowledge Items:\n{knowledge_corpus}"
        
        response = client.chat.completions.create(
            model="gpt-4o",  # The newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Extract IDs from result
        if isinstance(result, dict) and "ids" in result:
            relevant_ids = result["ids"]
        elif isinstance(result, list):
            relevant_ids = result
        else:
            # Try to find IDs in response
            relevant_ids = result.get("ids", [])
        
        # Filter original knowledge items to keep order
        relevant_items = [item for item in knowledge_items if item["id"] in relevant_ids]
        
        return relevant_items
        
    except Exception as e:
        print(f"Error performing semantic search: {str(e)}")
        
        # Method 2: Fallback to basic keyword search when API is unavailable
        print("Falling back to basic keyword search...")
        query_terms = query.lower().split()
        
        # Score each knowledge item based on keyword matches
        scored_items = []
        for item in knowledge_items:
            content = item.get('content', '').lower()
            
            # Simple scoring mechanism
            score = 0
            for term in query_terms:
                if term in content:
                    # Add a score based on term frequency
                    score += content.count(term)
                    
                    # Bonus points for terms in the first 100 characters (likely the title/summary)
                    if term in content[:100]:
                        score += 5
            
            # Check for exact phrase match (significant boost)
            if query.lower() in content:
                score += 20
            
            # Add employee name and department information to the search scope
            if 'employee_name' in item and any(term in item['employee_name'].lower() for term in query_terms):
                score += 10
                
            if 'department' in item and any(term in item['department'].lower() for term in query_terms):
                score += 10
                
            # Add the item to our results if it has a positive score
            if score > 0:
                scored_items.append((item, score))
        
        # Sort items by score (descending) and return the top 5
        sorted_items = [item for item, score in sorted(scored_items, key=lambda x: x[1], reverse=True)]
        return sorted_items[:5]
