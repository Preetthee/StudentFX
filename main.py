from tools import *

amount, src, dst, deadline = 1000, "USD", "BDT", 30
res = recommend_routes(amount, src, dst, deadline, tier=SUGGEST)
print(explain(res))

route = res["cheapest_on_time"]
token = new_confirmation(route, amount)
print("To approve, confirm with:", token)
print(simulate_transfer(route, amount, tier=EXECUTE_SANDBOX, confirm_token=token, expected_token=token))
