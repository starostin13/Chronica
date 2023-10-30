import random
import string

def numberToMonthNameRu(n):
    match n:
        case 1: return ("январе")
        case 2: return ("феврале")
        case 3: return ("марте")
        case 4: return ("апреле")
        case 5: return ("мае")
        case 6: return ("июне")
        case 7: return ("июле")
        case 8: return ("августе")
        case 9: return ("сентябре")
        case 10: return ("октябре")
        case 11: return ("ноябре")
        case 12: return ("декабре")
        

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str