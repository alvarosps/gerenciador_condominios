from num2words import num2words

def number_to_words(value):
    try:
        return num2words(float(value), lang='pt_BR')
    except Exception as e:
        print(f"Erro ao converter número para extenso: {e}")
        return value

def format_currency(value):
    return f"R${value:,.2f}"