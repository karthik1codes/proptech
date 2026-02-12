"""
Natural Language Command Parser
Detects intents and extracts entities from WhatsApp messages
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CommandIntent(Enum):
    """Supported command intents."""
    # Floor Control
    CLOSE_FLOOR = "close_floor"
    OPEN_FLOOR = "open_floor"
    
    # Simulation
    SIMULATE = "simulate"
    WHAT_IF = "what_if"
    RUN_OPTIMIZATION = "run_optimization"
    
    # Dashboard & Analytics
    SHOW_DASHBOARD = "show_dashboard"
    EXECUTIVE_SUMMARY = "executive_summary"
    PORTFOLIO_OVERVIEW = "portfolio_overview"
    PROPERTY_DETAILS = "property_details"
    
    # Reports
    DOWNLOAD_PDF = "download_pdf"
    ENERGY_REPORT = "energy_report"
    
    # Recommendations
    GET_RECOMMENDATIONS = "get_recommendations"
    
    # Reset
    RESET_PROPERTY = "reset_property"
    RESET_ALL = "reset_all"
    UNDO = "undo"
    
    # Alerts
    CHECK_ALERTS = "check_alerts"
    SUBSCRIBE_ALERTS = "subscribe_alerts"
    UNSUBSCRIBE_ALERTS = "unsubscribe_alerts"
    
    # System
    HELP = "help"
    STATUS = "status"
    LIST_PROPERTIES = "list_properties"
    
    # MCP Tools
    MCP_TOOL = "mcp_tool"
    
    # Unknown
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Parsed command result."""
    intent: CommandIntent
    property_name: Optional[str] = None
    property_id: Optional[str] = None
    floors: List[int] = None
    parameters: Dict[str, Any] = None
    confidence: float = 1.0
    raw_message: str = ""
    
    def __post_init__(self):
        if self.floors is None:
            self.floors = []
        if self.parameters is None:
            self.parameters = {}


class CommandParser:
    """
    Natural language command parser for WhatsApp messages.
    Uses pattern matching and keyword detection for intent classification.
    """
    
    # Property name patterns (will be populated with actual property names)
    property_patterns: Dict[str, str] = {}
    
    # Floor number patterns
    FLOOR_PATTERNS = [
        r'(?:floor|f|level|lvl)\s*(\d+)',  # floor 7, f7, level 3
        r'(\d+)(?:st|nd|rd|th)?\s*floor',   # 7th floor, 3rd floor
        r'floors?\s*([\d,\s]+)',             # floors 2, 4, 5
        r'f([\d,\s]+)',                       # f2,4,5
    ]
    
    # Intent patterns (order matters - more specific first)
    INTENT_PATTERNS = {
        # Floor Control
        CommandIntent.CLOSE_FLOOR: [
            r'close\s+(?:floor|f|level|lvl)',
            r'shut\s+(?:down\s+)?(?:floor|f)',
            r'disable\s+(?:floor|f)',
            r'close\s+f?\d',
        ],
        CommandIntent.OPEN_FLOOR: [
            r'open\s+(?:floor|f|level|lvl)',
            r'enable\s+(?:floor|f)',
            r'activate\s+(?:floor|f)',
            r'reopen\s+(?:floor|f)',
        ],
        
        # Simulation
        CommandIntent.SIMULATE: [
            r'simulat',
            r'what\s*if',
            r'what\s+happens\s+if',
            r'project',
        ],
        CommandIntent.RUN_OPTIMIZATION: [
            r'run\s+optimiz',
            r'optimiz',
            r'run\s+analysis',
        ],
        
        # Dashboard
        CommandIntent.SHOW_DASHBOARD: [
            r'(?:show|view|get)\s+dashboard',
            r'dashboard',
            r'main\s+view',
        ],
        CommandIntent.EXECUTIVE_SUMMARY: [
            r'executive\s+summary',
            r'exec\s+summary',
            r'summary',
            r'overview',
        ],
        CommandIntent.PORTFOLIO_OVERVIEW: [
            r'portfolio',
            r'all\s+properties',
        ],
        CommandIntent.PROPERTY_DETAILS: [
            r'(?:show|view|get)\s+(?:details|info|analytics)',
            r'details\s+(?:for|of|about)',
            r'analytics\s+(?:for|of)',
        ],
        
        # Reports
        CommandIntent.DOWNLOAD_PDF: [
            r'download\s+(?:pdf|report)',
            r'pdf\s+report',
            r'generate\s+(?:pdf|report)',
            r'send\s+(?:pdf|report)',
            r'get\s+(?:pdf|report)',
        ],
        CommandIntent.ENERGY_REPORT: [
            r'energy\s+(?:report|savings|analysis)',
            r'power\s+(?:report|savings)',
            r'electricity\s+(?:report|savings)',
        ],
        
        # Recommendations
        CommandIntent.GET_RECOMMENDATIONS: [
            r'recommend',
            r'suggest',
            r'advice',
            r'tips',
            r'what\s+should',
        ],
        
        # Reset
        CommandIntent.RESET_PROPERTY: [
            r'reset\s+property',
            r'reset\s+\w+\s+(?:tech|park|center|tower|hub)',
            r'clear\s+(?:changes|overrides)',
        ],
        CommandIntent.RESET_ALL: [
            r'reset\s+all',
            r'clear\s+all',
            r'start\s+fresh',
        ],
        CommandIntent.UNDO: [
            r'undo',
            r'revert',
            r'go\s+back',
        ],
        
        # Alerts
        CommandIntent.CHECK_ALERTS: [
            r'(?:check|view|show)\s+alerts?',
            r'alerts?$',
            r'active\s+alerts?',
        ],
        CommandIntent.SUBSCRIBE_ALERTS: [
            r'subscribe',
            r'enable\s+alerts?',
            r'turn\s+on\s+alerts?',
        ],
        CommandIntent.UNSUBSCRIBE_ALERTS: [
            r'unsubscribe',
            r'disable\s+alerts?',
            r'turn\s+off\s+alerts?',
            r'stop\s+alerts?',
        ],
        
        # System
        CommandIntent.HELP: [
            r'^help$',
            r'(?:show|view)\s+help',
            r'commands?',
            r'what\s+can\s+you\s+do',
        ],
        CommandIntent.STATUS: [
            r'^status$',
            r'system\s+status',
        ],
        CommandIntent.LIST_PROPERTIES: [
            r'^list$',
            r'list\s+properties',
            r'show\s+properties',
            r'^properties$',
        ],
        
        # MCP Tools
        CommandIntent.MCP_TOOL: [
            r'mcp\s+',
            r'tool\s+call',
        ],
    }
    
    def __init__(self, properties: List[Dict[str, Any]] = None):
        """
        Initialize the command parser.
        
        Args:
            properties: List of property dictionaries with 'name' and 'property_id'
        """
        self.properties = properties or []
        self._build_property_patterns()
    
    def _build_property_patterns(self):
        """Build regex patterns for property name matching."""
        self.property_patterns = {}
        
        for prop in self.properties:
            name = prop.get("name", "")
            prop_id = prop.get("property_id", "")
            
            if name and prop_id:
                # Create pattern variations
                name_lower = name.lower()
                # Full name
                self.property_patterns[name_lower] = prop_id
                
                # First word (e.g., "Horizon" from "Horizon Tech Park")
                first_word = name_lower.split()[0]
                if first_word not in self.property_patterns:
                    self.property_patterns[first_word] = prop_id
                
                # Abbreviated versions (e.g., "HTP" from "Horizon Tech Park")
                words = name.split()
                if len(words) > 1:
                    abbrev = ''.join(w[0] for w in words).lower()
                    if abbrev not in self.property_patterns:
                        self.property_patterns[abbrev] = prop_id
    
    def update_properties(self, properties: List[Dict[str, Any]]):
        """Update the property list and rebuild patterns."""
        self.properties = properties
        self._build_property_patterns()
    
    def parse(self, message: str) -> ParsedCommand:
        """
        Parse a message and extract intent and entities.
        
        Args:
            message: The raw message text
            
        Returns:
            ParsedCommand with intent, property, floors, and parameters
        """
        message_lower = message.lower().strip()
        
        # Detect intent
        intent = self._detect_intent(message_lower)
        
        # Extract property
        property_name, property_id = self._extract_property(message_lower)
        
        # Extract floors
        floors = self._extract_floors(message_lower)
        
        # Extract additional parameters
        parameters = self._extract_parameters(message_lower, intent)
        
        # Calculate confidence
        confidence = self._calculate_confidence(intent, property_id, floors)
        
        return ParsedCommand(
            intent=intent,
            property_name=property_name,
            property_id=property_id,
            floors=floors,
            parameters=parameters,
            confidence=confidence,
            raw_message=message
        )
    
    def _detect_intent(self, message: str) -> CommandIntent:
        """Detect the command intent from the message."""
        # Check each intent pattern in order
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return intent
        
        # Check if it's just a property name query
        _, prop_id = self._extract_property(message)
        if prop_id and len(message.split()) <= 3:
            return CommandIntent.PROPERTY_DETAILS
        
        return CommandIntent.UNKNOWN
    
    def _extract_property(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract property name and ID from the message."""
        message_lower = message.lower()
        
        # Try to match property patterns
        best_match = None
        best_length = 0
        
        for pattern, prop_id in self.property_patterns.items():
            if pattern in message_lower:
                if len(pattern) > best_length:
                    best_match = prop_id
                    best_length = len(pattern)
        
        if best_match:
            # Find the property name
            for prop in self.properties:
                if prop.get("property_id") == best_match:
                    return prop.get("name"), best_match
        
        return None, None
    
    def _extract_floors(self, message: str) -> List[int]:
        """Extract floor numbers from the message."""
        floors = set()
        
        for pattern in self.FLOOR_PATTERNS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str):
                    # Handle comma-separated floors
                    nums = re.findall(r'\d+', match)
                    for num in nums:
                        floors.add(int(num))
        
        return sorted(list(floors))
    
    def _extract_parameters(self, message: str, intent: CommandIntent) -> Dict[str, Any]:
        """Extract additional parameters based on intent."""
        params = {}
        
        # Extract percentages
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', message)
        if pct_match:
            params["percentage"] = float(pct_match.group(1))
        
        # Extract intensity/level
        intensity_match = re.search(r'(?:intensity|level)\s*[:=]?\s*(\d+(?:\.\d+)?)', message)
        if intensity_match:
            params["intensity"] = float(intensity_match.group(1))
        
        # Extract time period
        if "week" in message:
            params["period"] = "weekly"
        elif "month" in message:
            params["period"] = "monthly"
        elif "year" in message:
            params["period"] = "yearly"
        
        return params
    
    def _calculate_confidence(
        self,
        intent: CommandIntent,
        property_id: Optional[str],
        floors: List[int]
    ) -> float:
        """Calculate confidence score for the parsed command."""
        confidence = 0.5  # Base confidence
        
        if intent != CommandIntent.UNKNOWN:
            confidence += 0.3
        
        if property_id:
            confidence += 0.15
        
        if floors:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def get_help_text(self) -> str:
        """Get help text for available commands."""
        return """🤖 *PropTech Copilot - Commands*

━━━━━━━━━━━━━━━━━━
*🏢 Floor Control*
━━━━━━━━━━━━━━━━━━
• *Close F7 in Horizon* - Close floor 7
• *Open floor 3* - Reopen floor 3
• *Close floors 2,4,5* - Close multiple floors

━━━━━━━━━━━━━━━━━━
*📊 Simulation*
━━━━━━━━━━━━━━━━━━
• *Simulate closing F3* - Run what-if analysis
• *What if we shut floor 2?*
• *Run optimization*

━━━━━━━━━━━━━━━━━━
*📈 Analytics*
━━━━━━━━━━━━━━━━━━
• *Show dashboard* - View main metrics
• *Executive summary* - Portfolio overview
• *Horizon details* - Property analytics

━━━━━━━━━━━━━━━━━━
*📄 Reports*
━━━━━━━━━━━━━━━━━━
• *Download PDF* - Get summary report
• *Energy report* - Energy savings analysis

━━━━━━━━━━━━━━━━━━
*🔄 Reset*
━━━━━━━━━━━━━━━━━━
• *Reset Horizon* - Reset property state
• *Reset all* - Reset all overrides
• *Undo* - Revert last change

━━━━━━━━━━━━━━━━━━
*🔔 Alerts*
━━━━━━━━━━━━━━━━━━
• *Alerts* - View active alerts
• *Subscribe* - Enable auto-alerts
• *Unsubscribe* - Disable alerts

━━━━━━━━━━━━━━━━━━
*📋 General*
━━━━━━━━━━━━━━━━━━
• *List* - Show all properties
• *Status* - System status
• *Help* - Show this menu"""


# Global instance
command_parser: Optional[CommandParser] = None


def init_command_parser(properties: List[Dict[str, Any]]) -> CommandParser:
    """Initialize the global command parser."""
    global command_parser
    command_parser = CommandParser(properties)
    return command_parser
