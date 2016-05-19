#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unicodedata
import mwlib.parser.nodes
from mwlib.cdb.cdbwiki import WikiDB
from mwlib.uparser import parseString
from mwlib import nuwiki

class MediaWikiWikiSegmenter(object):
    # see http://meta.wikimedia.org/wiki/Help:HTML_in_wikitext
    blockTags = {
        'br': True, ### NOTE
        'blockquote': True, 'caption': True,
        'center': True, 'dd': True,  'div': True,
        'dl': True, 'dt': True,
        'h1': True, 'h2': True, 'h3': True,
        'h4': True, 'h5': True, 'h6': True,
        'li': True, 'ol': True, 'p': True,
        'pre': True,
        'th': True, 'td': True,
        'ul': True }
    styleTags = {
        'abbr': True, 'b': True, 'big': True,
        'cite': True, 'code': True, 'del': True,
        'em': True, 'font': True, 'i': True, 'ins': True,
        'ruby': True, 'rb': True,
        's': True, 'small': True, 'span': True,
        'strike': True, 'strong': True,
        'sub': True, 'sup': True, 'tt': True, 
        'u': True, 'var': True }
    ignoreTags = { 'hr': True, 'table': True, 'tr': True }
    stopTags = {
        'references': True, 'ref': True,  # ignore references now
        'rt': True
        }

    def action(self, node):
        action = {}
        if hasattr(node, 'blocknode') and node.blocknode is True or \
                isinstance(node, mwlib.parser.nodes.ItemList) or \
                isinstance(node, mwlib.parser.nodes.Cell):
            # blocknode includes node, mwlib.parser.nodes.Paragraph
            action['NEW_BLOCK'] = 1
        elif isinstance(node, mwlib.parser.nodes.Row):
            pass
        elif isinstance(node, mwlib.parser.nodes.Style) or \
                (isinstance(node, mwlib.parser.nodes.TagNode) and \
                     node.tagname == 'span'):
            action['BEGIN_SEGMENTATION'] = 1
            action['END_SEGMENTATION'] = 1
        elif isinstance(node, mwlib.parser.nodes.Text):
            try:
                action['TEXT'] = node.caption
            except AttributeError:
                pass
        elif isinstance(node, mwlib.parser.nodes.Article):
            pass
        elif isinstance(node, mwlib.parser.nodes.Math) or \
                isinstance(node, mwlib.parser.nodes.Timeline):
            pass
        elif isinstance(node, mwlib.parser.nodes.Link):
            # ignore SpecialLink, InterWikiLink, etc
            if isinstance(node, mwlib.parser.nodes.ArticleLink):
                action['BEGIN_SEGMENTATION'] = 1
                action['END_SEGMENTATION'] = 1

                # only piped link has a Text child??
                if node.colon is False and len(node.children) <= 0:
                    action['TEXT'] = node.target
                    action['STOP'] = 1

        elif isinstance(node, mwlib.parser.nodes.URL) or \
                isinstance(node, mwlib.parser.nodes.NamedURL):
            pass
        elif hasattr(node, 'type') and node.type == 'node':
            # dummy?
            pass
        else:
            tagname = (node.tagname or node.rawtagname) # ???
            if tagname is None:
                pass
                # print >>sys.stderr, node.__dict__
            elif tagname in MediaWikiWikiSegmenter.blockTags:
                action['NEW_BLOCK'] = 1
            elif tagname in MediaWikiWikiSegmenter.styleTags:
                action['BEGIN_SEGMENTATION'] = 1
                action['END_SEGMENTATION'] = 1
            elif tagname in MediaWikiWikiSegmenter.stopTags:
                action['STOP'] = 1
            elif tagname in MediaWikiWikiSegmenter.ignoreTags:
                pass
            else:
                pass
                # print >>sys.stderr, node.__dict__
        return action

    def traverse(self, node, output, depth):
        action = self.action(node)

        if 'SKIP' in action:
            return output

        if 'NEW_BLOCK' in action:
            # condition for reusing the last empty block
            if not (len(output) >= 1 and \
                        (len(output[-1]) <= 0 or \
                             (len(output[-1]) == 1 and \
                                  output[-1][-1] == ''))):
                output.append([])
        if 'BEGIN_SEGMENTATION' in action:
            if len(output) <= 0:
                output.append([])
            if len(output[-1]) <= 0 or not output[-1][-1] == '':
                output[-1].append('')
        if 'TEXT' in action:
            if len(output) <= 0:
                output.append([])
            if len(output[-1]) <= 0:
                output[-1].append(action['TEXT'])
            else:
                output[-1][-1] += action['TEXT']
        if 'STOP' not in action:
            for c in node.children:
                output = self.traverse(c, output, depth + 1)
        if 'END_SEGMENTATION' in action:
            output[-1].append('')
        return output

    def cleanOutput(self, output):
        rv = []
        for l in output:
            if len(l) <= 0:
                continue
            if len(l[-1]) == '':
                l2 = l[:-1]
            else:
                l2 = l
            hasLetter = False
            for seg in l2:
                for uchar in seg:
                    if not isinstance(uchar, unicode):
                        uchar = unicode(uchar)
                    if unicodedata.category(uchar)[0] == 'L': # Letter
                        hasLetter = True
                        break
            if hasLetter:
                rv.append(l2)
        return rv

    def printOutput(self, output, ostream=sys.stdout, doSegment=True):
        if doSegment:
            segLetter = '+'
        else:
            segLetter = ''
        for l in output:
            print >>ostream, segLetter.join(map(lambda x: x.replace('+', '\+'), l)).encode('utf-8')
        

def main():
    segmenter = MediaWikiWikiSegmenter()
    templdb = nuwiki.adapt(WikiDB(templdbPath, lang="ja"))

    contentdb = WikiDB(contentdbPath, lang="ja")

    for title, text in contentdb.reader.iteritems():
        tree = parseString(title=title, raw=text, wikidb=templdb)

        print >>sys.stderr, title.encode("utf-8")
        output = segmenter.traverse(tree, [], 0)
        output = segmenter.cleanOutput(output)
        segmenter.printOutput(output, False)

if __name__ == "__main__":
    main()
