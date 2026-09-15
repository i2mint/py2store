# py2store.ext.wordnet

This moved to lexis project

The py2store wrapper to nltk.corpus.wordnet. Your no fuss gateway to (English) words.

The easiest way to get nltk.corpus.wordnet is

```text
pip install nltk
```

in your terminal, and then in a python console:

```default
import nltk; nltk.download('wordnet')
```

If you don’t like that way, [see here](https://www.nltk.org/install.html) for other ways to get wordnet.

The central construct of this module is the Synset (a set of synonyms that share a common meaning).
To see a few things you can do with Synsets, naked, [see here](https://www.nltk.org/howto/wordnet.html).

Here we put a py2store wrapper around this stuff.

What is WordNet? [https://wordnet.princeton.edu/](https://wordnet.princeton.edu/)
