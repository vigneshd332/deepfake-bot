import logging
import re
import numpy as np
import nltk
from nltk.tag import pos_tag
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('words')
nltk.download('stopwords')

STOP_WORDS = set(stopwords.words('english'))


def tokenize(text):
    """Returns clean, tokenized words"""
    # Remove all the special characters and empty spaces:
    text = re.sub(r'\[[0-9]*\]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # Tokenize
    tokens = nltk.word_tokenize(text.lower())

    # Lemmatize
    return [nltk.stem.WordNetLemmatizer().lemmatize(token) for token in tokens]


WORD_VECTORIZER = TfidfVectorizer(tokenizer=tokenize,
                                  stop_words='english')


def cleanse_words(s):
    """Returns a list of non-stopwords with punctuation stripped away in lower case"""
    s = re.sub(r'[^\w\s#]', ' ', s).lower()
    words = s.split(' ')
    result = []
    for w in words:
        res = w.strip()
        if res not in STOP_WORDS and len(res) > 1 and res not in result:
            result.append(res)

    return result


def select_by_cosine_similarity(prompt, possible_responses):
    """Chooses the reply with the closest cosine similarity to the prompt"""

    possible_responses.append(prompt)
    response_vectors = WORD_VECTORIZER.fit_transform(possible_responses)

    # Calculate cosine similarities
    cosine_sims = cosine_similarity(response_vectors[-1], response_vectors)

    # Index of the second best cosine similarity (the best will be the prompt itself)
    best_match = cosine_sims.argsort()[0][-2]

    # Check the values
    cosine_sim_values = cosine_sims.flatten()
    cosine_sim_values.sort()

    # If all the scores are 0, just return the first response that isn't None
    if cosine_sim_values[-2] == 0:
        for res in possible_responses:
            if res is not None:
                return res
    else:
        return possible_responses[best_match]


def select_by_matching_words(prompt, candidate_replies):
    """Chooses the reply which contains the most words found in the prompt"""
    # calculate a score for each candidate
    words_to_match = cleanse_words(prompt)
    scores = []
    for s in candidate_replies:
        clean_reply = cleanse_words(s)
        count = 0
        for word in words_to_match:
            if word in clean_reply:
                count += 1
        scores.append(count)

    # Return the first reply having the max score
    for i in range(len(candidate_replies)):
        if scores[i] == max(scores) and candidate_replies[i] is not None:
            return candidate_replies[i]


def normal_with_min(avg, std, minimum):
    """Used to calculate delay times"""
    result = np.random.normal(avg, std)
    if result < minimum:
        result = minimum
    return result


def capitalized(word):
    """Checks if a word is capitalized"""
    if len(word) > 1:
        return word[0].isupper() and word[1:].lower() == word[1:]
    else:
        return False


def punctuate(sentence):
    """Adds periods to markovify sentences in places where they seem to be missing"""

    # Identify proper nouns and possessives. We don't need to punctuate places before these.
    tagged_sentence = pos_tag(sentence.split())
    possessives = [word for word in sentence if word.endswith("'s") or word.endswith("s'")]
    proper_nouns = [word for word, pos in tagged_sentence if pos == 'NNP' or word.lower() == 'i']

    # Identify the places that need periods.
    need_periods = []
    for k in sentence.split()[1:]:
        if k not in proper_nouns and k not in possessives and capitalized(k):
            idx = sentence.find(k)
            end_char = sentence[idx - 2]
            if end_char.isalpha() or end_char.isdigit():
                need_periods.append(idx - 1)

    # Add the periods in.
    for i in range(len(need_periods)):
        idx = need_periods[i] + i
        sentence = sentence[:idx] + '.' + sentence[idx:]

    return sentence
