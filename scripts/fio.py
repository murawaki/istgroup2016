#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import codecs
import sys
import re
import time
from StringIO import StringIO
from subprocess import Popen, PIPE
from zenhan import z2h

def escaped_split(s, delim):
    ret = []
    current = []
    itr = iter(s)
    for ch in itr:
        if ch == '\\':
            try:
                # skip the next character; it has been escaped!
                current.append('\\')
                current.append(next(itr))
            except StopIteration:
                pass
        elif ch == delim:
            # split! (add current to the list and reset it)
            ret.append(''.join(current))
            current = []
        else:
            current.append(ch)
    ret.append(''.join(current))
    return ret

def block_edatree_iter(f):
    buf = ""
    for line in f:
        line = line.rstrip("\n\r")
        if len(line) <= 0:
            if len(buf) > 0:
                yield buf + "\n"
            buf = ""
        else:
            buf += line + "\n"
    if len(buf) > 0:
        yield buf + "\n"

def block_selected_iter(f):
    buf = []
    for line in f:
        line = line.rstrip("\n\r")
        if line == "EOS":
            assert(len(buf) > 0)
            yield buf
            buf = []
        else:
            buf.append(line)

class FormattingException(Exception):
    def __str__(self):
        return repr(self.args[0])


class ConfSeg(object):
    def __init__(self, word_list, wseg_scores, _id=None):
        self._id = _id
        self.word_list = word_list
        self.wseg_scores = wseg_scores

    def dumps(self):
        return " ".join(map(lambda x: x["surface"], self.word_list)) + "\n" \
            + " ".join(map(lambda x: str(abs(x)), self.wseg_scores))

    def dumpsraw(self):
        return "".join(map(lambda x: x["surface"], self.word_list))

    @classmethod
    def load(self, f):
        _id = 1
        while True:
            # 1st line: word list
            line = f.next()
            line = line.rstrip("\n\r")
            word_list = map(lambda x: { "surface": x }, line.split(" "))
            # 2nd line: prob
            line = f.next()
            line = line.rstrip("\n\r")
            if len(line) > 0:
                wseg_scores = map(lambda x: float(x), line.split(" "))
            else:
                # one-character input
                wseg_scores = []
            # 3rd line: empty
            line = f.next()
            line = line.rstrip()
            if len(line) > 0:
                raise FormattingException("malformed input: %s" % line)
            pos = 0
            for word in word_list:
                l = len(word["surface"])
                for i in xrange(1, l):
                    wseg_scores[pos + i - 1] *= -1
                pos += l
            yield ConfSeg(word_list, wseg_scores, _id=_id)
            _id += 1


class Kkci(object):
    def __init__(self, word_list, _id=None):
        self._id = _id
        self.word_list = word_list

    def dumps(self):
        return " ".join(map(lambda x: x["surface"] + "/" + x["yomi"], self.word_list)) + "\n"

    def dumpsraw(self):
        return "".join(map(lambda x: x["surface"], self.word_list))

    def dumpstree(self):
        # pseudo-tree
        rv = "ID=%s\n" % (self._id if self._id is not None else "-1")
        for word in self.word_list:
            _padding = word["_padding"] if "_padding" in word else " "
            pid = word["pid"] if "pid" in word else "-1"
            cat = word["cat"] if "cat" in word else "*"
            line = "%s %s %s%s%s" % (word["wid"], pid, word["surface"], _padding, cat)
            if "misc" in word:
                line += "".join(word["misc"])
            rv += line + "\n"
        rv += "\n"
        return rv

    @classmethod
    def load(self, f):
        _id = 1
        for line in f:
            word_list = []
            line = line.rstrip()
            for i, sy in enumerate(line.split(" ")): # escape?
                surface, yomi = sy.split("/", 1)
                word_list.append({ "surface": surface, "cat": yomi, "wid": ("%03d" % (i + 1)) })
            yield Kkci(word_list, _id=_id)
            _id += 1
            

class EdaTree(object):
    STATE_U = 0
    STATE_S = 1
    STATE_B = 2
    space_re = re.compile(r"(\s+)")

    def __init__(self, word_list, _id):
        self._id = _id
        self.word_list = word_list

    def dumps(self):
        rv = "ID=%s\n" % self._id
        for word in self.word_list:
            _padding = word["_padding"] if "_padding" in word else " "
            line = "%s %s %s%s%s" % (word["wid"], word["pid"], word["surface"], _padding, word["cat"])
            if "misc" in word:
                line += "".join(word["misc"])
            rv += line + "\n"
        rv += "\n"
        return rv

    def dumpsraw(self):
        return "".join(map(lambda x: x["surface"], self.word_list))

    def dumpstree(self):
        return self.dumps()

    @classmethod
    def load(self, f):
        _id = None
        buf = []
        state = self.STATE_U
        for line in f:
            line = line.rstrip()
            if line.startswith("ID="):
                if state != self.STATE_U:
                    raise FormattingException("malformed input: %s" % line)
                state = self.STATE_S
                _id = line[3:]
            elif len(line) > 0:
                if state == self.STATE_U:
                    raise FormattingException("malformed input: %s" % line)
                state = self.STATE_B
                tokens = self.space_re.split(line)
                word = {}
                word["wid"] = tokens.pop(0)
                tokens.pop(0)
                word["pid"] = tokens.pop(0)
                tokens.pop(0)
                word["surface"] = tokens.pop(0)
                word["_padding"] = tokens.pop(0)
                word["cat"] = tokens.pop(0)
                if len(tokens) > 0:
                    # tokens.pop(0)
                    word["misc"] = tokens
                buf.append(word)
            else:
                if state == self.STATE_S:
                    raise FormattingException("malformed input: %s" % line)
                state = self.STATE_U
                if len(buf) > 0:
                    yield self(buf, _id)
                    buf = []
        if len(buf) > 0:
            yield self(buf, _id)


class WikiEdaTree(EdaTree):
    WIKI_O = 0
    WIKI_B = 1
    WIKI_I = 2

    def dumps(self):
        rv = "ID=%s\n" % self._id
        for word in self.word_list:
            _padding = word["_padding"] if "_padding" in word else " "
            line = "%s %s %s%s%s" % (word["wid"], word["pid"], word["surface"], _padding, word["cat"])
            if word["stype"] == self.WIKI_B:
                line += word["_wpadding"] + "B " + word["entity"]
            elif word["stype"] == self.WIKI_I:
                line += word["_wpadding"] + "I"
            rv += line + "\n"
        rv += "\n"
        return rv

    @classmethod
    def load(self, f):
        for wseq in super(WikiEdaTree, self).load(f):
            eposlist = []
            for i, word in enumerate(wseq.word_list):
                if "misc" in word and len(word["misc"]) > 0:
                    if len(word["misc"]) < 2: # space B/I
                        raise FormattingException("malformed annotation: %s" % "".join(word["misc"]))
                    word["_wpadding"] = word["misc"].pop(0)
                    stype = word["misc"].pop(0)
                    if stype not in ("B", "I"):
                        raise FormattingException("malformed annotation: %s" % "".join(word["misc"]))
                    if stype == "B":
                        word["stype"] = self.WIKI_B
                        word["misc"].pop(0)
                        word["entity"] = "".join(word["misc"])
                        del word["misc"]
                        eposlist.append(i)
                    else:
                        if i <= 0 \
                           or "stype" not in wseq.word_list[i - 1] \
                           or wseq.word_list[i - 1]["stype"] not in (self.WIKI_B, self.WIKI_I):
                            raise FormattingException("malformed annotation: I-without-B: %s" % word["wid"])
                        word["stype"] = self.WIKI_I
                        self.WIKI_I
                else:
                    word["stype"] = self.WIKI_O
            for epos in eposlist:
                mention_orig = wseq.word_list[epos]["surface"]
                for i in xrange(epos + 1, len(wseq.word_list)):
                    if wseq.word_list[i]["stype"] == self.WIKI_I:
                        mention_orig += wseq.word_list[i]["surface"]
                    else:
                        break
                wseq.word_list[epos]["mention"] = z2h(mention_orig, mode=3)
            yield wseq


class KyTea(object):
    space_re = re.compile(r"\s+")

    def __init__(self, kytea_path=None, kytea_model=None):
        cmd_args = ["kytea", "-notags", "-out", "conf"]
        if kytea_path is not None:
            cmd_args[0] = kytea_path
        if kytea_model is not None:
            cmd_args.append("-model")
            cmd_args.append(kytea_model)
        self.p = None
        self._enc = codecs.getencoder("utf-8")
        self._dec = codecs.getdecoder("utf-8")
        self.cmd_args = cmd_args

    def open(self):
        self.p = Popen(self.cmd_args, stdin=PIPE, stdout=PIPE, close_fds=True)

    def __del__(self):
        if self.p is None:
            return
        if self.p.poll() is not None:
            self.p.stdin.close()
            self.p.kill()
            self.p.wait()
        self.p = None

    def get_wseq(self, line):
        if not line.endswith("\n"):
            line += "\n"
        if self.p is None:
            self.open()
        self.p.stdin.write(self._enc(line)[0])
        self.p.stdin.flush()
        buf = self.p.stdout.readline()
        buf += self.p.stdout.readline()
        buf += self.p.stdout.readline()
        buf = self._dec(buf)[0]
        f = StringIO(buf)
        wseq = ConfSeg.load(f).next()
        return wseq


def main():
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

    for wseq in EdaTree.load(codecs.getreader("utf-8")(sys.stdin)):
        sys.stdout.write(wseq.dumpsraw() + "\n")

if __name__ == "__main__":
    main()
