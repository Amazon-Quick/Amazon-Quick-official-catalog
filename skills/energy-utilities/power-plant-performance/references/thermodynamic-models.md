# Thermodynamic Models and Ambient Corrections

Formula and code reference for the cycle modeling and heat rate workflows.

## Steam property availability (read this first)

The Amazon Quick Python sandbox does NOT include CoolProp or an IAPWS steam
table library, and pip install is blocked. You cannot compute water/steam
enthalpy and entropy from pressure and temperature inside the sandbox. For any
Rankine or bottoming-cycle calculation you must obtain state-point properties
(h, s, quality) from one of:
- state-point data the user uploaded (plant instrumentation or a steam table
  export),
- values the user provides when asked, or
- an authoritative steam table source fetched during the session.
- a coding agent such as Kiro via ACP in Quick on desktop, used to install
  CoolProp and compute enthalpy, entropy, and quality from pressure and
  temperature outside the sandbox when full-fidelity steam properties are
  required.

Never fabricate enthalpy or entropy values. This is the Rule 0 constraint
applied to thermodynamics. Brayton (ideal-gas) calculations below rely only on
stable physical constants and are safe to compute directly with numpy.

## Rankine Cycle (steam plants)

Four processes:
1. 1->2 Isentropic compression (pump): W_pump = v1 * (P2 - P1) ~= h2 - h1
2. 2->3 Constant-pressure heat addition (boiler): Q_in = h3 - h2
3. 3->4 Isentropic expansion (turbine): W_turbine = h3 - h4
4. 4->1 Constant-pressure heat rejection (condenser): Q_out = h4 - h1

Thermal efficiency:
```
eta_Rankine = ((h3 - h4) - (h2 - h1)) / (h3 - h2)
```
Simplified when pump work is small:
```
eta_Rankine ~= (h3 - h4) / (h3 - h2)
```

Reheat cycle (states 4->5 reheat in boiler, 5->6 LP expansion):
```
eta_reheat = ((h3 - h4) + (h5 - h6) - (h2 - h1)) / ((h3 - h2) + (h5 - h4))
```

Feedwater heater performance:
```
TTD = T_sat(P_extraction) - T_fw_out    [F]
DCA = T_drain - T_fw_in                  [F]
```
Out-of-service heater penalty: ~15-25 BTU/kWh per heater (varies by extraction).

Condenser back-pressure effect: ~100-150 BTU/kWh per 1 inch Hg increase in
condenser pressure (typical coal plant).

## Brayton Cycle (gas turbines)

Uses ideal-gas relations with physical constants; safe to compute in the sandbox.
```python
import numpy as np
gamma = 1.4        # ratio of specific heats for air at moderate temperature
cp = 1.005         # kJ/(kg*K) for air
T1 = 288.15        # K, ISO 15 C
rp = 18            # compressor pressure ratio (F-class example)
T3 = 1673          # K, turbine inlet temperature example (1400 C)
eta_c = 0.88       # compressor isentropic efficiency (use plant value)
eta_t = 0.92       # turbine isentropic efficiency (use plant value)

T2_ideal = T1 * rp ** ((gamma - 1) / gamma)
T4_ideal = T3 / rp ** ((gamma - 1) / gamma)
T2_actual = T1 + (T2_ideal - T1) / eta_c
T4_actual = T3 - eta_t * (T3 - T4_ideal)

w_c = cp * (T2_actual - T1)     # kJ/kg
w_t = cp * (T3 - T4_actual)     # kJ/kg
q_in = cp * (T3 - T2_actual)    # kJ/kg
w_net = w_t - w_c
bwr = w_c / w_t                 # back-work ratio, typically 0.40-0.55
eta_brayton = w_net / q_in
```
Ideal efficiency check: `eta_ideal = 1 - 1 / rp ** ((gamma - 1) / gamma)`.

Typical F-class heavy-duty GT: pressure ratio 15-20:1, TIT 1300-1400 C, simple
cycle efficiency 36-40% (LHV), exhaust temperature 590-640 C.

## Combined Cycle Heat Balance

Overall efficiency:
```
eta_CC = 1 - (1 - eta_GT) * (1 - eta_HRSG * eta_ST)
```
Example: eta_GT = 0.40, eta_ST = 0.35, eta_HRSG = 0.85 gives
eta_CC = 1 - 0.60 * (1 - 0.2975) = 0.578 (57.8%).

HRSG performance:
```
Q_recovered = m_exhaust * Cp_exhaust * (T_exhaust_in - T_stack)
Q_available = m_exhaust * Cp_exhaust * (T_exhaust_in - T_ambient)
HRSG_effectiveness = Q_recovered / Q_available
```
Pinch point: `Pinch = T_gas_at_evaporator_exit - T_saturation(P_drum)`, design
8-15 C. Setting pinch below ~5 C predicts unrealistic heat recovery.
Approach: `Approach = T_saturation(P_drum) - T_feedwater_at_economizer_exit`,
typically 5-10 C. Track GT and ST performance separately.

## Ambient Condition Corrections

ISO reference conditions: 15 C (59 F), 101.325 kPa (14.696 psia), 60% relative
humidity. Apply corrections before comparing to design or across periods.

Gas turbine power correction:
```
P_corrected = P_measured * CF_temp * CF_pressure * CF_humidity
CF_temp     = 1 - K_temp * (T_ambient_C - 15)      # K_temp ~ 0.005-0.007 per C
CF_pressure = P_ambient_kPa / 101.325
CF_humidity = 1 - K_hum * (omega - omega_ISO)       # small, ~1-2% max
```
Rule of thumb: ~0.4% power loss per 1 F above 59 F.

Heat rate correction:
```
HR_corrected = HR_measured / (1 + K_HR * (T_ambient_C - 15))   # K_HR ~ 0.001 per C
```
Rule of thumb: ~0.1% heat rate increase per 1 F above 59 F. These linear
approximations are valid within about +/-20 C of ISO.

Steam turbine back-pressure correction (water-cooled condensers):
```
P_condenser ~= P_sat(T_CW_in + TTD + Terminal_Difference)
```
Correction ~100-150 BTU/kWh per inch Hg above design condenser pressure.

Example GT correction snippet:
```python
t_ambient_C = (t_ambient_F - 32) * 5 / 9
cf_temp = 1 - 0.006 * (t_ambient_C - 15)
cf_pressure = p_ambient_kpa / 101.325
hr_corrected = hr_measured / (1 + 0.001 * (t_ambient_C - 15))
power_corrected = power_measured / (cf_temp * cf_pressure)
```
