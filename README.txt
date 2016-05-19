
1. Python wrapper to KyTea

Requirements:
- Download/install KyTea from http://www.phontron.com/kytea/

>>> from fio import KyTea
>>> kytea = KyTea()
>>> sent = kytea.get_wseq(u"外国人参政権")
>>> sent.wseg_scores
[-1.60124, 2.69359, 0.422593, -0.503634, 0.819813]

The 1st item -1.60124 is the score for the boundary between 外 and 国.
The negative value suggests KyTea will not place a boundary at this point.

You can specify KyTea's path and/or model path.
>>> kytea = KyTea(kytea_path="/path/to/kytea", kytea_model="/path/to/kytea_model")



2. mwlib

Requirements:
- mwlib
  - get the latest version by
    % git clone https://github.com/pediapress/mwlib.git
      NOTE: the latest release (version 0.15.14) has not supported localized redirects yet
    % cd mwlib
    % python setup.py install
- mwlib.cdb
    % pip install mwlib.cdb


  1. Download an XML dump of Japanese Wikipedia jawiki-201?????-pages-meta-current.xml.bz2
     from http://dumps.wikimedia.org/jawiki/ (or its mirror)
     Hereafter this file is referred to as $(WIKIDUMP)

  2. Convert $(WIKIDUMP) to CDB data
     % mw-buildcdb --input $(WIKIDUMP) --output $(CDBDIR)

  3. Extract article titles (excluding redirects, disambiguation pages, etc.)
     % python scripts/list_article_titles.py $(CDBDIR) > jawiki.titles.txt


fetching the content of the article "外国人参政権"

>>> from mwlib.cdb.cdbwiki import WikiDB
>>> db = WikiDB("jawiki-20150512", lang="ja")
>>> print db.reader[u"外国人参政権"]

scripts/parse_mediawiki.py is an example of how to use mwlib to parse wikitext.


3. SVM

See http://scikit-learn.org/stable/modules/svm.html#svm
