import pandas as pd
from io import StringIO

vendors_csv = """vendor_id,name,service_type,zip,radius_km,rating,price_band,speed_score,base_fee,hourly_rate
V_ELEC_1,"SparkRight Electric","ELECTRICIAN",95054,15,4.5,3,3,80,90
V_APPL_1,"QuickFix Appliances","APPLIANCE_REPAIR",95051,20,4.6,3,4,90,95
V_APPL_2,"Budget Appliance Repair","APPLIANCE_REPAIR",95051,15,4.0,1,2,60,70
V_GAS_1,"SafeGas Services","GAS_TECHNICIAN",95050,20,4.9,4,5,120,110
V_PLUMB_FAST,"RapidFlow Plumbing","PLUMBER",95054,20,4.7,4,5,110,100
V_PLUMB_BALANCED,"ValuePlumb","PLUMBER",95054,25,4.5,3,4,90,80
V_PLUMB_CHEAP,"SaverPlumb","PLUMBER",95054,25,4.0,1,2,60,65
V_HVAC_FAST,"CoolBreeze HVAC","HVAC",95054,25,4.6,4,5,130,110
V_HVAC_CHEAP,"BudgetAir HVAC","HVAC",95054,25,4.1,2,2,80,85
"""

def load_vendors_df():
    return pd.read_csv(StringIO(vendors_csv))

# Singleton instance
vendors_df = load_vendors_df()