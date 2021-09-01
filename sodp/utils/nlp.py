import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize 
from fuzzywuzzy import fuzz

SIMILARITY_RATIO = 80

# given a sentence, retrieve the relevant keywords
def getKeywords(sentence):
    # first remove stopwords
    stop_words = set(stopwords.words('english'))
    
    # now tokenize
    text_tokens = word_tokenize(sentence)
    final_tokens = [word for word in text_tokens if not word in stopwords.words()]

    return final_tokens

# check if cluster has some words in keywords or title
def belongsToCluster(cluster, words):
    cluster_words = cluster.split(",")

    # now for each of the words check if they have similarity with the ones in the cluster
    for word in words:
        for cluster_word in cluster_words:
            ratio = fuzz.ratio(word.lower(), cluster_word.lower())
            if ratio >= SIMILARITY_RATIO:
                return True

    return False

