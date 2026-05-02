from django.urls import path
from .views import (
    graph_common_words,
    graph_tweets_vs_oil,
    graph_tweets_vs_oil_by_publisher,
    get_latest_prediction,
    graph_prediction_accuracy,
)

urlpatterns = [
    path("graph/common-words/", graph_common_words),
    path("graph/tweets-vs-oil/", graph_tweets_vs_oil),
    path("graph/tweets-vs-oil-by-publisher/", graph_tweets_vs_oil_by_publisher),

    path("prediction/", get_latest_prediction),
    path("prediction/accuracy/", graph_prediction_accuracy),
]