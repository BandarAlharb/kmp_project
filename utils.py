from datetime import datetime, timedelta
import time

def format_timestamp(timestamp):
    """Format Unix timestamp to human-readable format"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_relative_time(timestamp):
    """Format Unix timestamp to relative time (e.g., '2 hours ago')"""
    now = datetime.now()
    dt = datetime.fromtimestamp(timestamp)
    diff = now - dt
    
    # Calculate the difference
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds // 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    else:
        return format_timestamp(timestamp)

def truncate_text(text, max_length=100):
    """Truncate text to specified length and add ellipsis if needed"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def get_sample_departments():
    """Return a list of sample department names for the organization"""
    return [
        "Engineering",
        "Marketing",
        "Sales",
        "Human Resources",
        "Finance",
        "Operations",
        "Research & Development",
        "Customer Support",
        "Legal",
        "Product Management",
        "Administration"
    ]

def is_within_timeframe(timestamp, days=5):
    """Check if a timestamp is within the specified timeframe (in days)"""
    now = datetime.now()
    dt = datetime.fromtimestamp(timestamp)
    diff = now - dt
    
    return diff.days <= days

def convert_to_timestamp(date_str):
    """Convert date string to Unix timestamp"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())

def get_date_ranges(days=30):
    """Get date ranges for time filtering"""
    today = datetime.now()
    date_ranges = {}
    
    # Today
    date_ranges["today"] = today.strftime("%Y-%m-%d")
    
    # Last 24 hours
    date_ranges["24h"] = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Last 5 days
    date_ranges["5d"] = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    
    # Last 30 days
    date_ranges["30d"] = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    
    return date_ranges
