import os

# 1. 查全部變數
# print(dict(os.environ))

# 2. 查特定變數（例如：查看 PATH）
print(os.environ.get('ADMIN_USERNAME'))
