from datetime import datetime
import pandas as pd

class KnowledgeManager:
    """Class to manage knowledge operations and analytics"""
    
    def __init__(self, dynamodb):
        """Initialize with database connection"""
        self.db = dynamodb
    
    def get_department_activity(self):
        """Generate department activity report"""
        from database import get_knowledge, get_ideas
        
        # Get all knowledge items
        knowledge_items = get_knowledge(self.db)
        
        # Get all ideas
        ideas = get_ideas(self.db)
        
        # Aggregate by department
        departments = {}
        
        # Process knowledge contributions
        for item in knowledge_items:
            dept = item.get('department', 'Unknown')
            if dept not in departments:
                departments[dept] = {
                    'knowledge_count': 0,
                    'ideas_count': 0,
                    'last_activity': None
                }
            
            departments[dept]['knowledge_count'] += 1
            
            # Track last activity
            timestamp = item.get('timestamp', 0)
            if not departments[dept]['last_activity'] or timestamp > departments[dept]['last_activity']:
                departments[dept]['last_activity'] = timestamp
        
        # Process ideas
        for idea in ideas:
            dept = idea.get('department', 'Unknown')
            if dept not in departments:
                departments[dept] = {
                    'knowledge_count': 0,
                    'ideas_count': 0,
                    'last_activity': None
                }
            
            departments[dept]['ideas_count'] += 1
            
            # Track last activity
            timestamp = idea.get('timestamp', 0)
            if not departments[dept]['last_activity'] or timestamp > departments[dept]['last_activity']:
                departments[dept]['last_activity'] = timestamp
        
        # Convert timestamps to datetime for display
        for dept in departments:
            if departments[dept]['last_activity']:
                departments[dept]['last_activity'] = datetime.fromtimestamp(
                    departments[dept]['last_activity']
                ).strftime('%Y-%m-%d %H:%M:%S')
        
        return departments
    
    def get_activity_over_time(self):
        """Generate activity timeline data for charts"""
        from database import get_knowledge, get_ideas
        
        # Get all items
        knowledge_items = get_knowledge(self.db)
        ideas = get_ideas(self.db)
        
        # Prepare dataframes
        k_data = []
        for item in knowledge_items:
            timestamp = item.get('timestamp', 0)
            k_data.append({
                'date': datetime.fromtimestamp(timestamp).date(),
                'type': 'knowledge',
                'department': item.get('department', 'Unknown')
            })
        
        i_data = []
        for item in ideas:
            timestamp = item.get('timestamp', 0)
            i_data.append({
                'date': datetime.fromtimestamp(timestamp).date(),
                'type': 'idea',
                'department': item.get('department', 'Unknown')
            })
        
        # Combine data
        combined_data = pd.DataFrame(k_data + i_data)
        
        # Get activity by date
        if not combined_data.empty:
            activity_by_date = combined_data.groupby(['date', 'type']).size().unstack().fillna(0)
            
            # Convert to list format for Streamlit charts
            dates = activity_by_date.index.tolist()
            knowledge_counts = activity_by_date.get('knowledge', [0] * len(dates)).tolist()
            idea_counts = activity_by_date.get('idea', [0] * len(dates)).tolist()
            
            return {
                'dates': [d.strftime('%Y-%m-%d') for d in dates],
                'knowledge': knowledge_counts,
                'ideas': idea_counts
            }
        else:
            # Return empty data structure
            return {
                'dates': [],
                'knowledge': [],
                'ideas': []
            }
    
    def get_top_contributors(self, limit=10):
        """Get top knowledge contributors"""
        from database import get_knowledge
        
        # Get all knowledge items
        knowledge_items = get_knowledge(self.db)
        
        # Count contributions by employee
        contributors = {}
        for item in knowledge_items:
            employee = item.get('employee_name', 'Anonymous')
            if employee in contributors:
                contributors[employee] += 1
            else:
                contributors[employee] = 1
        
        # Sort by count (descending)
        sorted_contributors = sorted(
            contributors.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Return top N
        return sorted_contributors[:limit]
    
    def get_popular_ideas(self, limit=5):
        """Get most popular ideas based on supporter count"""
        from database import get_ideas
        
        # Get all ideas
        ideas = get_ideas(self.db)
        
        # Sort by number of supporters
        sorted_ideas = sorted(
            ideas, 
            key=lambda x: len(x.get('supporters', [])), 
            reverse=True
        )
        
        # Return top N
        return sorted_ideas[:limit]
