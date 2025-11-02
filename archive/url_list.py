# Generate a list of URLS from the site in the format preferred by Epsilla

# for idx in range(1, 300):
#     print(f'https://tgn.phfactor.net/{item}.0/episode/index.html')

oddballs = [214.5, 206.5, 143.5, 20.5, 16.5, 14.5, 260.5, 282.5, 295.5, 300.0]

for item in oddballs:
    print(f'https://tgn.phfactor.net/{item}/episode/index.html')
