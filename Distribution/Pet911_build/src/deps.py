import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime, timedelta
import warnings
import csv
import json
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.manifold import TSNE
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import re
import string
from collections import Counter
from nltk.corpus import stopwords
import pymorphy3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import chi2