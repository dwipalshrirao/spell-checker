import sys
inp = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
# inp = [-3, -1, -4, -2]
largest_sum = 0
largst_smarr = []

if all(i < 0 for i in inp):
    largest_num = -10000000
    for i in inp:
        if i > largest_num:
            largest_num = i
    print(largest_num)
    sys.exit()

st , end = 0, 0
while st < len(inp)-1:
    end+=1

    # print(st, end)
    if sum(inp[st:end]) > largest_sum:
        largest_sum = sum(inp[st:end])
        largst_smarr = inp[st:end]
    

    if end > len(inp)-1:
        st+=1
        end = st + 1
    

print(sum(largst_smarr))

