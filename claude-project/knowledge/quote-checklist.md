# Quote checklist

What we need before a producer can quote. The quote-intake skill reads this table: the field key, which lines need it ("all" means every quote), and the question to ask the customer when it is missing.

| Field key | Needed for | Ask the customer |
|---|---|---|
| customer_name | all | What is your full name? |
| contact | all | What is the best phone number or email to reach you? |
| line_of_business | all | Which insurance do you want a quote for: auto, home, commercial or life? |
| effective_date | all | What date do you want the new policy to start? |
| zip_code | all | What is your ZIP code? |
| drivers | auto | Who will drive the vehicle, and what is each driver's date of birth? |
| vehicles | auto | What is the year, make and model (or VIN) of each vehicle? |
| property_address | home | What is the address of the property? |
| year_built | home | What year was the home built? |
| square_feet | home | About how many square feet is the home? |
| roof_age | home | How old is the roof? |
| business_type | commercial | What does your business do? |
| annual_revenue | commercial | What is your annual revenue? |
| employee_count | commercial | How many employees do you have? |
| years_in_business | commercial | How many years have you been in business? |
| date_of_birth | life | What is your date of birth? |
| coverage_amount | life | How much coverage do you want? |
| tobacco_use | life | Do you use tobacco? |

Optional, recorded when given: current_carrier, current_premium, notes.

Rules:
- Never guess a value. If the email does not say it, it is missing.
- Write dates and amounts exactly as the customer wrote them.
- One email can ask for more than one line (for example auto and home). Then every line's fields are needed.
