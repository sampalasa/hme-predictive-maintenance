"""Shared constants: business thresholds and reference values.

Centralizing these thresholds means the feature engineering, dashboard and
prediction layers all reason about "high temperature" or "critical vibration"
using the same numbers.
"""

# --- Sensor risk thresholds (derived from domain knowledge of HME sensors) ---
ENGINE_TEMP_WARNING_C = 95.0
ENGINE_TEMP_CRITICAL_C = 110.0

HYDRAULIC_PRESSURE_WARNING_BAR = 300.0
HYDRAULIC_PRESSURE_CRITICAL_BAR = 340.0

VIBRATION_WARNING_MM_S = 5.0
VIBRATION_CRITICAL_MM_S = 7.0

# --- Equipment types present in the HME_Downtime dataset ---
EQUIPMENT_TYPES = [
    "Excavator",
    "Loader",
    "Drill",
    "Grader",
    "Truck",
    "Dozer",
]

# --- User roles ---
ROLE_ADMIN = "Admin"
ROLE_ENGINEER = "Ingenieur"
ROLE_TECHNICIAN = "Technicien"
ROLE_MANAGER = "Manager"

ALL_ROLES = [ROLE_ADMIN, ROLE_ENGINEER, ROLE_TECHNICIAN, ROLE_MANAGER]

# --- Maintenance priority levels (ordinal) ---
PRIORITY_LOW = "Low"
PRIORITY_MEDIUM = "Medium"
PRIORITY_HIGH = "High"
PRIORITY_CRITICAL = "Critical"

PRIORITY_ORDER = [PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]

# --- Rolling window sizes (in number of readings) used by feature engineering ---
ROLLING_WINDOW_SHORT = 3
ROLLING_WINDOW_LONG = 7
