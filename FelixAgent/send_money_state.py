"""State management for Send Money Agent."""

from typing import Optional
from dataclasses import dataclass


@dataclass
class SendMoneyState:
    """Tracks the state of a money transfer request across multiple turns."""
    
    # Required fields
    amount: Optional[float] = None
    currency: Optional[str] = None
    beneficiary_account: Optional[str] = None  # Primary identifier
    beneficiary_name: Optional[str] = None    # Secondary, attached to account
    country: Optional[str] = None
    delivery_method: Optional[str] = None
    
    def update_field(self, field_name: str, value: any) -> None:
        """Update a field value."""
        if field_name in ['amount', 'currency', 'beneficiary_account', 'beneficiary_name', 'country', 'delivery_method']:
            setattr(self, field_name, value)
    
    def is_complete(self) -> bool:
        """Check if all required fields are collected."""
        return all([
            self.amount is not None,
            self.currency is not None,
            self.beneficiary_account is not None,
            self.country is not None,
            self.delivery_method is not None
        ])
    
    def get_summary(self) -> dict:
        """Get a summary of all collected information."""
        return {
            'amount': self.amount,
            'currency': self.currency,
            'beneficiary_account': self.beneficiary_account,
            'beneficiary_name': self.beneficiary_name,
            'country': self.country,
            'delivery_method': self.delivery_method,
        }

