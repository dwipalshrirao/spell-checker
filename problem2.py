inp = 'AAAAD'

st = 0
end = 1
cur_sb_set = set()
# while st < end:
#     cur_sb_set

for i in range(len(inp)):
    if i not in cur_sb_set:
        cur_sb_set.add(i)
        
