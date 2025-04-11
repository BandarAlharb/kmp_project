import boto3
import json
import os
import time
from datetime import datetime, timedelta
import uuid

# AWS DynamoDB tables
KNOWLEDGE_TABLE = "KMP_Knowledge"
PULSE_TABLE = "KMP_OrganizationPulse"
IDEAS_TABLE = "KMP_Ideas"
DEPARTMENTS_TABLE = "KMP_Departments"

def initialize_db():
    """Initialize AWS DynamoDB connection"""
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    
    # Create tables if they don't exist
    create_tables_if_not_exist(dynamodb)
    
    return dynamodb

def create_tables_if_not_exist(dynamodb):
    """Create necessary DynamoDB tables if they don't exist"""
    try:
        existing_tables = [table.name for table in dynamodb.tables.all()]
        
        # Create Knowledge table if it doesn't exist
        if KNOWLEDGE_TABLE not in existing_tables:
            dynamodb.create_table(
                TableName=KNOWLEDGE_TABLE,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
        
        # Create Pulse table if it doesn't exist
        if PULSE_TABLE not in existing_tables:
            dynamodb.create_table(
                TableName=PULSE_TABLE,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
        
        # Create Ideas table if it doesn't exist
        if IDEAS_TABLE not in existing_tables:
            dynamodb.create_table(
                TableName=IDEAS_TABLE,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
        
        # Wait for tables to be created
        for table_name in [KNOWLEDGE_TABLE, PULSE_TABLE, IDEAS_TABLE]:
            if table_name not in existing_tables:
                table = dynamodb.Table(table_name)
                table.wait_until_exists()

    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        # If tables can't be created, we'll continue and handle errors at runtime

# Knowledge Management Functions
def save_knowledge(dynamodb, content, department, employee_name):
    """Save knowledge item to DynamoDB"""
    table = dynamodb.Table(KNOWLEDGE_TABLE)
    
    item_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    item = {
        'id': item_id,
        'content': content,
        'department': department,
        'employee_name': employee_name,
        'timestamp': timestamp,
        'created_at': datetime.utcnow().isoformat()
    }
    
    table.put_item(Item=item)
    return item_id

def get_knowledge(dynamodb, item_id=None):
    """Get knowledge items from DynamoDB"""
    table = dynamodb.Table(KNOWLEDGE_TABLE)
    
    if item_id:
        response = table.get_item(Key={'id': item_id})
        return response.get('Item')
    else:
        response = table.scan()
        return response.get('Items', [])

def search_knowledge(dynamodb, query):
    """Search knowledge items based on query"""
    # In a production app, you'd use AWS ElasticSearch or other search services
    # For simplicity, we'll perform a more enhanced filtered scan here
    table = dynamodb.Table(KNOWLEDGE_TABLE)
    
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        if not items:
            print("No items found in knowledge table.")
            return []
            
        # Break query into terms for more flexible matching
        query_terms = query.lower().split()
        
        if not query_terms:
            return []
            
        # Score each item based on matching terms
        scored_items = []
        
        for item in items:
            content = item.get('content', '').lower()
            department = item.get('department', '').lower()
            employee = item.get('employee_name', '').lower()
            
            # Calculate a match score
            score = 0
            
            # Check for term matches in content
            for term in query_terms:
                if term in content:
                    # Count occurrences for content weighting
                    occurences = content.count(term)
                    score += min(occurences * 2, 10)  # Cap to avoid overwhelming results
                    
                # Check exact match in department or employee name (higher weight)
                if term in department:
                    score += 5
                    
                if term in employee:
                    score += 5
            
            # Exact phrase match is a strong signal
            if query.lower() in content:
                score += 15
                
            # Items with any match are added to results
            if score > 0:
                scored_items.append((item, score))
        
        # Sort by score (descending)
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # Return the items without scores
        return [item for item, _ in scored_items]
        
    except Exception as e:
        print(f"Error searching knowledge: {str(e)}")
        # In case of error, return an empty list
        return []

# Organization Pulse Functions
def add_pulse_update(dynamodb, title, content, department):
    """Add organization pulse update to DynamoDB"""
    table = dynamodb.Table(PULSE_TABLE)
    
    item_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    item = {
        'id': item_id,
        'title': title,
        'content': content,
        'department': department,
        'timestamp': timestamp,
        'created_at': datetime.utcnow().isoformat()
    }
    
    table.put_item(Item=item)
    return item_id

def get_pulse_updates(dynamodb, days=5):
    """Get organization pulse updates for the last X days"""
    table = dynamodb.Table(PULSE_TABLE)
    
    # Calculate timestamp for X days ago
    days_ago = int((datetime.utcnow() - timedelta(days=days)).timestamp())
    
    # Scan with filter (using ExpressionAttributeNames to handle reserved keyword)
    response = table.scan(
        FilterExpression="#ts >= :timestamp_val",
        ExpressionAttributeNames={
            "#ts": "timestamp"
        },
        ExpressionAttributeValues={
            ":timestamp_val": days_ago
        }
    )
    
    # Sort by timestamp (newest first)
    items = response.get('Items', [])
    items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return items

# Ideas & Initiatives Functions
def add_idea(dynamodb, title, description, employee_name, department):
    """Add new idea/initiative to DynamoDB"""
    table = dynamodb.Table(IDEAS_TABLE)
    
    item_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    item = {
        'id': item_id,
        'title': title,
        'description': description,
        'employee_name': employee_name,
        'department': department,
        'timestamp': timestamp,
        'created_at': datetime.utcnow().isoformat(),
        'supporters': [],
        'status': 'proposed'  # proposed, in_progress, completed, rejected
    }
    
    table.put_item(Item=item)
    return item_id

def get_ideas(dynamodb):
    """Get all ideas/initiatives from DynamoDB"""
    table = dynamodb.Table(IDEAS_TABLE)
    
    response = table.scan()
    items = response.get('Items', [])
    
    # Sort by timestamp (newest first)
    items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return items

def update_idea_status(dynamodb, idea_id, new_status):
    """Update idea/initiative status"""
    table = dynamodb.Table(IDEAS_TABLE)
    
    table.update_item(
        Key={'id': idea_id},
        UpdateExpression="set #status = :s",
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':s': new_status}
    )

def support_idea(dynamodb, idea_id, employee_name):
    """Add support for an idea/initiative"""
    table = dynamodb.Table(IDEAS_TABLE)
    
    # Get current idea details
    response = table.get_item(Key={'id': idea_id})
    current_idea = response.get('Item', {})
    
    # Get current supporters list
    current_supporters = current_idea.get('supporters', [])
    
    # Add employee if not already supporting
    if employee_name not in current_supporters:
        current_supporters.append(employee_name)
        
        # Update supporters list
        table.update_item(
            Key={'id': idea_id},
            UpdateExpression="set supporters = :s",
            ExpressionAttributeValues={':s': current_supporters}
        )
    
    return current_supporters

# Dashboard Analytics Functions
def get_knowledge_stats(dynamodb):
    """Get knowledge sharing statistics for dashboard"""
    knowledge_items = get_knowledge(dynamodb)
    
    # Calculate stats
    total_items = len(knowledge_items)
    
    # Count by department
    departments = {}
    for item in knowledge_items:
        dept = item.get('department', 'Unknown')
        if dept in departments:
            departments[dept] += 1
        else:
            departments[dept] = 1
    
    # Count by time period
    now = datetime.utcnow()
    today_count = 0
    week_count = 0
    month_count = 0
    
    for item in knowledge_items:
        timestamp = item.get('timestamp', 0)
        item_dt = datetime.fromtimestamp(timestamp)
        
        if (now - item_dt).days < 1:
            today_count += 1
        
        if (now - item_dt).days < 7:
            week_count += 1
            
        if (now - item_dt).days < 30:
            month_count += 1
    
    return {
        'total': total_items,
        'by_department': departments,
        'today': today_count,
        'week': week_count,
        'month': month_count
    }

def get_ideas_stats(dynamodb):
    """Get ideas/initiatives statistics for dashboard"""
    ideas = get_ideas(dynamodb)
    
    # Calculate stats
    total_ideas = len(ideas)
    
    # Count by status
    status_counts = {
        'proposed': 0,
        'in_progress': 0,
        'completed': 0,
        'rejected': 0
    }
    
    # Count by department
    departments = {}
    
    # Calculate average supporters
    total_supporters = 0
    
    for idea in ideas:
        status = idea.get('status', 'proposed')
        if status in status_counts:
            status_counts[status] += 1
        
        dept = idea.get('department', 'Unknown')
        if dept in departments:
            departments[dept] += 1
        else:
            departments[dept] = 1
        
        supporters = idea.get('supporters', [])
        total_supporters += len(supporters)
    
    avg_supporters = total_supporters / total_ideas if total_ideas > 0 else 0
    
    return {
        'total': total_ideas,
        'by_status': status_counts,
        'by_department': departments,
        'avg_supporters': avg_supporters
    }
