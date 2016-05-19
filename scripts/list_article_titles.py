#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# dump article titles (pages in the main namespace)
#
import sys
import codecs
import re
from mwlib.cdb.cdbwiki import WikiDB
from mwlib import nuwiki
from mwlib.nshandling import nshandler, get_redirect_matcher
# from mwlib.uparser import parseString
from mwlib.expander import Expander, ArgumentList, flatten
from mwlib.templ.nodes import Template 

from htmlentitydefs import name2codepoint

def format_entity(s):
    def unescape(match):
        code = match.group(1)
        if code:
            return unichr(int(code, 10))
        else:
            code = match.group(2)
            if code:
                return unichr(int(code, 16))
            else:
                code = match.group(3)
                if code in name2codepoint:
                    return unichr(name2codepoint[code])
        return match.group(0)
    s = format_entity.entity_re.sub(unescape, s)
    s = format_entity.tag_re.sub('', s)
    return s

format_entity.name2codepoint = name2codepoint.copy()
format_entity.name2codepoint['apos'] = ord("'")
format_entity.entity_re = re.compile('&(?:#(\d+)|(?:#x([\da-fA-F]+))|([a-zA-Z]+));')
format_entity.tag_re = re.compile('\</?span[^\>]*>')


def extract_correct_title(fragment, title, contentdb):
    # fragment: text starting with an instance of the 記事名の制約 template
    # extract 'title' parameter by intercepting template expansion
    te = Expander(fragment, pagename=title, wikidb=contentdb)
    found = False
    node_list = [te.parsed]
    while True:
        node = node_list.pop(0)
        if isinstance(node, Template):
            found = True
            break
        if isinstance(node, tuple):
            for v in node:
                node_list.append(v)
        if len(node_list) <= 0:
            break
    if not found:
        return None

    var = []
    for x in node[1]:
        var.append(x)
    var = ArgumentList(args=var, expander=te, variables=ArgumentList(expander=te))
    try:
        correct_title = var.get(u"title", None)
        if not correct_title:
            correct_title = var.get(0, None)
    except Exception:
        return None
    if "\t" in correct_title:
        return None
    if "[[" in correct_title:
        # e.g. Image
        return None
    return correct_title


def main():
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

    # ChemAimai and others has parameters
    ambig_re = re.compile(u"\{\{\s*(?:[Aa]imai|[Dd]isambig|[Dd]ab|[Mm]athematical[ \_]disambiguation|[Mm]athdab|曖昧さ回避|学校名の曖昧さ回避|人名の曖昧さ回避|[Pp]eople-dab|[Hh]ndis|地名の曖昧さ回避|[Gg]eodis|山の曖昧さ回避|[Cc]hemAimai)\s*(?:\}\}|\|)")
    # Wi, Wtr, Wtsr, Wiktionary redirect, Softredirect, Soft redirect
    softredirect_re = re.compile(u"\{\{\s*(?:[Ww]i|[Ww]tr|[Ww]tsr|(?:[Ww]iktionary[ \_]|[Ss]oft[ \_]?)redirect)\s*(\||\}\})")
    # e.g., Shift_JIS, 恋のビギナーなんです (T_T)
    # wrongtitle_re = re.compile(u"\{\{\s*記事名の制約\s*\|\s*(?:title\s*=\s*)?([^\|\}]+)\s*")
    wrongtitle_re = re.compile(u"\{\{\s*記事名の制約\s*\|[^\n]+\n")
    nontext_re = re.compile(u"UNIQ\-.+\-QINU")

    db = WikiDB(sys.argv[1], lang="ja")
    contentdb = nuwiki.adapt(db)
    handler = nshandler(contentdb.siteinfo)
    redirect_re = get_redirect_matcher(contentdb.siteinfo)

    for title in db.reader.iterkeys():
        if handler.splitname(title)[0] != 0: # NS_MAIN namespace
            continue
        if title.startswith("WP:") \
                or title.startswith(u"モジュール:") \
                or title.startswith(u"LTA:"): # long-term abuse
            # not a valid namespace but used in jawiki
            sys.stderr.write("skip pseudo-namespace: %s\n" % title)
            continue

        pagetext = db.reader[title]
        # redirect_matcher uses ^, but MediaWiki ignores initial spaces
        # pagetext = re.sub(r"^\s*\n*", "", pagetext)
        a = redirect_re(pagetext)
        if a is not None:
            if handler.splitname(a)[0] == 0: # NS_MAIN namespace
                sys.stdout.write("REDIRECT\t%s\t%s\n" % (title, a))
            # else:
            #     sys.stderr.write("redirect from main namespace to another: %s -> %s\n" % (title, a))
            continue

        ambig_match = ambig_re.search(pagetext[0:8192])
        if ambig_match:
            # sys.stderr.write("disambiguation page: %s %s\n" % (title, ambig_match.group(0)))
            sys.stdout.write("AMBIG\t%s\n" % title)
            continue

        softredirect_match = softredirect_re.search(pagetext[0:1024])
        if softredirect_match:
            sys.stderr.write("softredirect ignored: %s\n" % title)
            continue

        # NOTE: this may contain wiki markups such as '' and <sup>...</sup>
        wrongtitle_match = wrongtitle_re.search(pagetext[0:1024])
        if wrongtitle_match:
            fragment = wrongtitle_match.group(0)
            correct_title = extract_correct_title(fragment, title, contentdb)
            if correct_title and correct_title != title:
                if nontext_re.search(correct_title) is not None:
                    # contain <math> or <nowiki>
                    sys.stderr.write("skip correct but invalid title: %s\t%s" % (title, correct_title))
                else:
                    correct_title = format_entity(correct_title)
                    # sys.stderr.write("decode: %s\t%s\n" % (correct_title, correct_title2))
                    sys.stderr.write("wrong title\t%s\t%s\n" % (title, correct_title))
                    sys.stdout.write("WRONGTITLE\t%s\t%s\n" % (title, correct_title))
            else:
                sys.stderr.write("skip possibly wrong title: %s\t%s" % (title, fragment))
        sys.stdout.write("%s\n" % title)


if __name__ == "__main__":
    main()
