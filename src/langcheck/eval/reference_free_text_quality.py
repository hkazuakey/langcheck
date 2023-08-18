from typing import List

import torch
from detoxify import Detoxify
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from langcheck.eval.eval_value import EvalValue
from langcheck.stats import compute_stats

_sentiment_model_path = "cardiffnlp/twitter-roberta-base-sentiment-latest"
_sentiment_tokenizer = None
_sentiment_model = None

_fluency_model_path = "prithivida/parrot_fluency_model"
_fluency_tokenizer = None
_fluency_model = None

_toxicity_model = None


def sentiment(generated_outputs: List[str]) -> EvalValue:
    '''Calculates the sentiment scores of the generated outputs between
    0 (Negative) and 1 (Positive) based on the Twitter-roBERTa-base model.

    Ref:
        https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest

    Args:
        generated_outputs: A list of model generated outputs to evaluate

    Returns:
        An EvalValue object
    '''
    global _sentiment_tokenizer, _sentiment_model

    if _sentiment_tokenizer is None or _sentiment_model is None:
        _sentiment_tokenizer = AutoTokenizer.from_pretrained(
            _sentiment_model_path)

        # There is a "Some weights are not used warning" but we ignore it because
        # that is intended.
        _sentiment_model = AutoModelForSequenceClassification.from_pretrained(
            _sentiment_model_path)

    input_tokens = _sentiment_tokenizer(generated_outputs,
                                        return_tensors='pt',
                                        padding=True)

    with torch.no_grad():
        # Probabilities of [negative, neutral, positive]
        probs = torch.nn.functional.softmax(
            _sentiment_model(**input_tokens).logits, dim=1)

    scores = (probs[:, 1] / 2 + probs[:, 2]).tolist()

    return EvalValue(metric_name='sentiment',
                     prompts=None,
                     generated_outputs=generated_outputs,
                     metric_values=scores)


def fluency(generated_outputs: List[str]) -> EvalValue:
    '''Calculates the fluency scores of the generated outputs between
    0 (Negative) and 1 (Positive) based on the parrot_fluency_model.

    Ref:
    https://huggingface.co/prithivida/parrot_fluency_model

    Args:
        generated_outputs: A list of model generated outputs to evaluate

    Returns:
        An EvalValue object
    '''
    global _fluency_tokenizer, _fluency_model

    if _fluency_tokenizer is None or _fluency_model is None:
        _fluency_tokenizer = AutoTokenizer.from_pretrained(_fluency_model_path)

        # There is a "Some weights are not used warning" but we ignore it because
        # that is intended.
        _fluency_model = AutoModelForSequenceClassification.from_pretrained(
            _fluency_model_path)

    input_tokens = _fluency_tokenizer(generated_outputs,
                                      return_tensors='pt',
                                      padding=True)

    with torch.no_grad():
        # Probabilities of [negative, neutral, positive]
        probs = torch.nn.functional.softmax(
            _fluency_model(**input_tokens).logits, dim=1)

    scores = probs[:, 1].tolist()

    return EvalValue(metric_name='fluency',
                     prompts=None,
                     generated_outputs=generated_outputs,
                     metric_values=scores)


def toxicity(generated_outputs: List[str]) -> EvalValue:
    '''Calculates the toxicity scores of the generated outputs between
    0 (Negative) and 1 (Positive) based on the "original" model of detxify.

    Ref:
        https://github.com/unitaryai/detoxify

    Args:
        generated_outputs: A list of model generated outputs to evaluate

    Returns:
        An EvalValue object
    '''
    global _toxicity_model
    if _toxicity_model is None:
        _toxicity_model = Detoxify('original')
    scores = _toxicity_model.predict(generated_outputs)['toxicity']

    return EvalValue(metric_name='toxicity',
                     prompts=None,
                     generated_outputs=generated_outputs,
                     metric_values=scores)


def flesch_reading_ease(generated_outputs: List[str]) -> EvalValue:
    '''
    Tests the readability of the generated texts based on the number of
    sentences & words & syllables in the text. The score is typically between
    0 and 100 (that is not guaranteed). If the score is high, it means the input
    text is difficult to read.

    See "How to Write Plain English" by Rudolf Franz Flesch for more details.

    Args:
        generated_outputs: A list of model generated outputs to evaluate

    Returns:
        An EvalValue object
    '''
    output_stats = [compute_stats(output) for output in generated_outputs]
    scores = [
        206.835 - 1.015 * (stat.num_words / stat.num_sentences) - 84.6 *
        (stat.num_syllables / stat.num_words) for stat in output_stats
    ]
    return EvalValue(metric_name='flesch_reading_ease',
                     prompts=None,
                     generated_outputs=generated_outputs,
                     metric_values=scores)


def flesch_kincaid_grade(generated_outputs: List[str]) -> EvalValue:
    '''
    Rates the readability of the generated texts in relation to U.S. grade
    levels. The returned value suggests the grade level required to understand
    the text. As Flesch reading ease, the score is cacluated based on the number
    of sentences & words & syllables in the text.

    See also:
        https://apps.dtic.mil/sti/citations/ADA006655

    Args:
        generated_outputs: A list of model generated outputs to evaluate

    Returns:
        An EvalValue object
    '''
    output_stats = [compute_stats(output) for output in generated_outputs]
    scores = [
        0.39 * (stat.num_words / stat.num_sentences) + 11.8 *
        (stat.num_syllables / stat.num_words) - 15.59 for stat in output_stats
    ]
    return EvalValue(metric_name='flesch_kincaid_grade',
                     prompts=None,
                     generated_outputs=generated_outputs,
                     metric_values=scores)