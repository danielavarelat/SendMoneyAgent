"""Utility functions for parsing and validating user input."""

import re
from typing import Optional, Tuple


# Supported countries and their currencies
COUNTRY_CURRENCY_MAP = {
    'MEXICO': 'MXN',
    'HONDURAS': 'HNL',
    'REPUBLICA DOMINICANA': 'DOP',
    'DOMINICAN REPUBLIC': 'DOP',
    'NICARAGUA': 'NIO',
    'COLOMBIA': 'COP',
    'EL SALVADOR': 'USD',
    'GUATEMALA': 'GTQ',
}

# Currency names and codes
CURRENCY_NAMES = {
    'MXN': ['mxn', 'peso mexicano', 'pesos mexicanos', 'mexican peso', 'mexican pesos'],
    'HNL': ['hnl', 'lempira', 'lempiras', 'honduran lempira'],
    'DOP': ['dop', 'peso dominicano', 'pesos dominicanos', 'dominican peso', 'dominican pesos'],
    'NIO': ['nio', 'córdoba', 'córdobas', 'cordoba', 'cordobas', 'nicaraguan córdoba'],
    'COP': ['cop', 'peso colombiano', 'pesos colombianos', 'colombian peso', 'colombian pesos'],
    'USD': ['usd', 'dollar', 'dollars', 'us dollar', 'dólar', 'dólares'],
    'GTQ': ['gtq', 'quetzal', 'quetzales', 'guatemalan quetzal'],
}

# Country name variations
COUNTRY_VARIANTS = {
    'MEXICO': ['mexico', 'méxico', 'mex'],
    'HONDURAS': ['honduras'],
    'REPUBLICA DOMINICANA': ['republica dominicana', 'república dominicana', 'dominican republic', 'dominicana', 'rd'],
    'NICARAGUA': ['nicaragua', 'nic'],
    'COLOMBIA': ['colombia', 'col'],
    'EL SALVADOR': ['el salvador', 'salvador'],
    'GUATEMALA': ['guatemala', 'guate'],
}

# Supported delivery methods
DELIVERY_METHODS = {
    'bank transfer', 'wire transfer', 'bank', 'wire',
    'mobile wallet', 'wallet', 'mobile',
    'cash pickup', 'pickup', 'cash',
    'card', 'debit card', 'credit card'
}


def extract_amount(text: str) -> Optional[float]:
    """Extract monetary amount from text - simple number extraction."""
    # Look for numbers - simple patterns
    patterns = [
        r'\$\s*(\d+(?:\.\d{1,2})?)',  # $100 or $100.50
        r'\b(\d{1,6}(?:\.\d{1,2})?)\b',  # Standalone number (1-6 digits, optional decimals)
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                amount = float(match.group(1))
                # Reasonable amount check (between 1 and 1,000,000)
                if 1 <= amount <= 1000000:
                    return amount
            except (ValueError, IndexError):
                continue
    return None


def extract_currency(text: str) -> Optional[str]:
    """Extract currency from text - handles codes attached to numbers (e.g., "100usd", "100U")."""
    text_lower = text.lower().strip()
    text_upper = text.upper()
    
    # First, try currency codes directly attached to numbers (e.g., "100usd", "100USD", "100U")
    # Match pattern: number followed by letters (could be full or partial currency)
    attached_match = re.search(r'\d+(?:\.\d{1,2})?([A-Z]{1,3})\b', text_upper)
    if attached_match:
        letters = attached_match.group(1)
        # Try to match as full currency code first
        if letters in CURRENCY_NAMES:
            return letters
        # Try partial match - if letters match start of any currency code
        for code in CURRENCY_NAMES.keys():
            if code.startswith(letters):
                return code
    
    # Try exact currency code match (3-letter codes with word boundaries)
    currency_code_match = re.search(r'\b([A-Z]{3})\b', text_upper)
    if currency_code_match:
        code = currency_code_match.group(1)
        if code in CURRENCY_NAMES:
            return code
    
    # Try currency names with word boundaries
    for code, names in CURRENCY_NAMES.items():
        for name in names:
            pattern = r'\b' + re.escape(name) + r'\b'
            if re.search(pattern, text_lower):
                return code
    
    return None


def extract_country(text: str) -> Optional[str]:
    """Extract country from text using intelligent matching with word boundaries."""
    text_lower = text.lower().strip()
    
    # Try to match country variants with word boundaries
    for country, variants in COUNTRY_VARIANTS.items():
        for variant in variants:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, text_lower):
                return country
    
    return None


def extract_account_number(text: str) -> Optional[str]:
    """Extract account number from text - handles various formats."""
    # Look for patterns like "ACC-123456", "AC12629233", "AC9Q834982", "account 123456", etc.
    # IMPORTANT: We check for country names first to avoid false matches
    # Extract country first to exclude it from account number matching
    text_for_account = text
    
    # Remove known country names from the text before extracting account numbers
    # This prevents "COLOMBIA" from being matched as an account number
    for country in COUNTRY_CURRENCY_MAP.keys():
        # Remove country name (case-insensitive) from text
        text_for_account = re.sub(r'\b' + re.escape(country) + r'\b', '', text_for_account, flags=re.IGNORECASE)
    
    patterns = [
        r'(?:account|acc|account number|account#|cuenta|cuenta número)\s*:?\s*([A-Z0-9-]+)',
        r'\b(AC[A-Z0-9]{6,})\b',  # AC12629233 or AC9Q834982 format - alphanumeric after AC
        r'\b(ACC-?[A-Z0-9]{6,})\b',  # ACC-123456 or ACC123456 or ACC-9Q834982
        r'\b([A-Z]{2,4}-?\d{6,})\b',  # Any 2-4 letters followed by 6+ DIGITS (not just alphanumeric)
        r'\b(\d{8,})\b',  # Standalone 8+ digit number (likely account)
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text_for_account, re.IGNORECASE)
        for match in matches:
            account = match.group(1).strip().upper()
            
            # Handle accounts with letters (like AC12629233, AC9Q834982)
            if any(c.isalpha() for c in account):
                # Has letters - likely an account number
                # Keep original format (AC12629233, AC9Q834982, ACC-123456, etc.)
                return account
            
            # Handle pure numbers (8+ digits)
            if len(account) >= 8 and account.replace('-', '').replace(' ', '').isdigit():
                # Pure number - format as ACC-XXXXXX
                return f"ACC-{account.replace('-', '')}"
    
    return None


def extract_beneficiary_name(text: str) -> Optional[str]:
    """Extract beneficiary name from text - handles names in any case without requiring trigger words."""
    # Common words to exclude
    excluded_words = {
        'the', 'a', 'an', 'hello', 'hi', 'hey', 'hola', 'good', 'morning', 
        'afternoon', 'evening', 'night', 'thanks', 'thank', 'please', 
        'yes', 'no', 'ok', 'okay', 'sure', 'alright', 'send', 'money',
        'dollars', 'pesos', 'usd', 'mxn', 'cop', 'hnl', 'dop', 'nio', 'gtq',
        'bank', 'transfer', 'card', 'wallet', 'pickup', 'cash', 'mobile',
        'mexico', 'honduras', 'colombia', 'nicaragua', 'guatemala', 'salvador',
        'dominican', 'republic', 'change', 'update', 'amount', 'currency',
        'to', 'for', 'with', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'someone', 'somebody', 'person', 'recipient', 'beneficiary'
    }
    
    # Exclude common phrases that might be mistaken for names
    excluded_phrases = [
        'send money', 'send money to', 'send to', 'money to', 'want to send',
        'help me send', 'i want to', 'would like to', 'need to send'
    ]
    
    # First check if text contains excluded phrases - if so, don't extract names
    text_lower = text.lower()
    for phrase in excluded_phrases:
        if phrase in text_lower:
            # If the text is mostly excluded phrases, don't extract a name
            # This prevents "send money to" from being extracted as a name
            return None
    
    # Look for name patterns - words that look like names (2+ letters, not all caps unless it's a short word)
    # Pattern: One or more words, each with 2+ letters
    # Accept: "john", "John", "JOHN", "john smith", "John Smith", "JOHN SMITH", "john smith garcia"
    pattern = r'\b([A-Za-z]{2,}(?:\s+[A-Za-z]{2,}){0,2})\b'
    
    matches = re.finditer(pattern, text)
    for match in matches:
        name = match.group(1).strip()
        name_lower = name.lower()
        
        # Skip if it's an excluded word
        if name_lower in excluded_words:
            continue
        
        # Skip if it contains excluded phrases
        if any(phrase in name_lower for phrase in excluded_phrases):
            continue
        
        # Skip if it's a country name
        if name.upper() in COUNTRY_CURRENCY_MAP:
            continue
        
        # Skip if it looks like a currency code (3 letters all caps)
        if len(name) == 3 and name.isupper() and name in CURRENCY_NAMES:
            continue
        
        # Skip if it's a number
        if name.replace(' ', '').isdigit():
            continue
        
        # Skip single letters or very short words
        if len(name.replace(' ', '')) <= 1:
            continue
        
        # Skip if it contains numbers (likely not a name)
        if re.search(r'\d', name):
            continue
        
        # Skip common phrases that might match
        if name_lower in ['send money', 'bank transfer', 'mobile wallet', 'cash pickup']:
            continue
        
        # Return the first valid name found (preserve original case)
        return name
    
    return None


def extract_delivery_method(text: str) -> Optional[str]:
    """Extract delivery method from text."""
    text_lower = text.lower()
    
    method_map = {
        'bank transfer': 'Bank Transfer',
        'wire transfer': 'Bank Transfer',
        'bank': 'Bank Transfer',
        'wire': 'Bank Transfer',
        'mobile wallet': 'Mobile Wallet',
        'wallet': 'Mobile Wallet',
        'mobile': 'Mobile Wallet',
        'cash pickup': 'Cash Pickup',
        'pickup': 'Cash Pickup',
        'cash': 'Cash Pickup',
        'card': 'Card',
        'debit card': 'Card',
        'credit card': 'Card'
    }
    
    for key, method in method_map.items():
        if key in text_lower:
            return method
    
    return None


def get_expected_formats() -> dict:
    """Get expected formats for each field to show in error messages."""
    return {
        'amount': 'a number (e.g., "100", "$100", "100.50")',
        'currency': 'a currency code or name. Supported: USD, MXN, HNL, DOP, NIO, COP, GTQ (or "dollars", "pesos", "quetzales", etc.)',
        'country': 'one of: ' + ', '.join(sorted(COUNTRY_CURRENCY_MAP.keys())),
        'beneficiary_account': 'an account number (e.g., "ACC-123456", "AC12629233", or just the number like "12629233")',
        'beneficiary_name': 'a person\'s name (e.g., "John Smith", "Maria Garcia")',
        'delivery_method': 'one of: Bank Transfer, Mobile Wallet, Cash Pickup, or Card',
    }

def validate_country_value(country: str) -> tuple[bool, Optional[str]]:
    """Validate country and return (is_valid, error_message)."""
    country_upper = country.upper()
    if country_upper in COUNTRY_CURRENCY_MAP:
        return True, None
    
    # Check for close matches
    for valid_country in COUNTRY_CURRENCY_MAP.keys():
        if country_upper in valid_country or valid_country in country_upper:
            return False, f"Did you mean '{valid_country}'? Supported countries are: {', '.join(sorted(COUNTRY_CURRENCY_MAP.keys()))}"
    
    return False, f"'{country}' is not a supported country. Supported countries are: {', '.join(sorted(COUNTRY_CURRENCY_MAP.keys()))}"


def validate_currency_value(currency: str) -> tuple[bool, Optional[str]]:
    """Validate currency and return (is_valid, error_message)."""
    currency_upper = currency.upper()
    currency_lower = currency.lower()
    
    # Check if it's a valid currency code
    if currency_upper in CURRENCY_NAMES:
        return True, None
    
    # Check if it matches any currency name
    for code, names in CURRENCY_NAMES.items():
        if currency_lower in names:
            return True, None
    
    # Get supported currencies from COUNTRY_CURRENCY_MAP
    supported_currencies = sorted(set(COUNTRY_CURRENCY_MAP.values()))
    supported = ', '.join(supported_currencies)
    return False, f"'{currency}' is not a supported currency. Supported currencies are: {supported}"


def validate_delivery_method_value(method: str) -> tuple[bool, Optional[str]]:
    """Validate delivery method and return (is_valid, error_message)."""
    method_lower = method.lower()
    
    valid_methods = {
        'bank transfer': 'Bank Transfer',
        'wire transfer': 'Bank Transfer',
        'bank': 'Bank Transfer',
        'wire': 'Bank Transfer',
        'mobile wallet': 'Mobile Wallet',
        'wallet': 'Mobile Wallet',
        'mobile': 'Mobile Wallet',
        'cash pickup': 'Cash Pickup',
        'pickup': 'Cash Pickup',
        'cash': 'Cash Pickup',
        'card': 'Card',
        'debit card': 'Card',
        'credit card': 'Card'
    }
    
    if method_lower in valid_methods:
        return True, None
    
    supported = 'Bank Transfer, Mobile Wallet, Cash Pickup, or Card'
    return False, f"'{method}' is not a supported delivery method. Supported methods are: {supported}"


def detect_correction(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect if user is making a correction and what field they're correcting.
    Returns (field_name, value_text) or (None, None).
    """
    text_lower = text.lower()
    
    # Pattern: "change [field] to [value]" or "change [field] [value]"
    change_pattern = re.search(r'change\s+(\w+)(?:\s+to\s+)?(.+)?', text_lower)
    if change_pattern:
        field_word = change_pattern.group(1)
        value_text = change_pattern.group(2) if change_pattern.group(2) else None
        
        # Map common field names to actual field names
        field_mapping = {
            'amount': 'amount',
            'country': 'country',
            'currency': 'currency',
            'beneficiary': 'beneficiary_name',
            'name': 'beneficiary_name',
            'account': 'beneficiary_account',
            'delivery': 'delivery_method',
            'method': 'delivery_method'
        }
        
        if field_word in field_mapping:
            return field_mapping[field_word], value_text.strip() if value_text else None
    
    return None, None

