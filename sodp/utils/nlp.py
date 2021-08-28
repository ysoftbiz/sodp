import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize 

# given a sentence, retrieve the relevant keywords
def getKeywords(sentence):
    # first remove stopwords
    stop_words = set(stopwords.words('english'))
    
    # now tokenize
    text_tokens = word_tokenize(sentence)
    final_tokens = [word for word in text_tokens if not word in stopwords.words()]

    return final_tokens

