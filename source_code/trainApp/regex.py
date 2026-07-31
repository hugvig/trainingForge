import re

def readline(line):
    print(line)
    info = re.findall("^(:?Exercice.):(:?.*):(:?.*):(:?.*)$", line)
    print(info)
    try:
        exercice_name = info[0][0]
        sets_reps = info[0][1]
        tempo = info[0][2]
        rest = info[0][3]

        print(f'{exercice_name}:\nsets:{sets_reps}\ntempo:{tempo}\nRest for {rest} after each set.')
    except IndexError:
        print("There was no match for the specified pattern. Please check that you followed the specified format.")


readline("Exercice1:3x2+1+1::2min")
