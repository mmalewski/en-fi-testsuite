#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, collections, re


# def analyzeSentence(sentence):
	# global analyzer
	# result = []
	# analyzer_out = analyzer.match(sentence)		# this only yields one analysis per word, which might be wrong
	# print(">", analyzer_out)
	# for wordresult in re.split(r'(?<=]) ', analyzer_out):
		# tagdict = {}
		# # this removes anything not in square brackets, e.g. punctuation
		# for match in re.finditer(r'\[([^=\]]+)=([^=\]]+)\]', wordresult):
			# tagdict[match.group(1)] = match.group(2)
		# result.append(tagdict)
	# return result

nelex = {l.split("\t")[0].strip(): l.split("\t")[1].strip() for l in open('ne-lex.txt', 'r', encoding='utf-8')}


def readAnalysis(analysisfile):
	line = analysisfile.readline()
	analysis = {}
	# word position is not important, as any occurrence of a word will have the same analysis
	currentword, currentwordfeatures, currentwordpos = "", set(), 1
	while not line.startswith('****\t'):
		if line.isspace():
			if len(currentwordfeatures) > 0:
				currentwordfeatures.add("@{}".format(currentwordpos))
				analysis[currentword] = currentwordfeatures
				currentword = ""
				currentwordfeatures = set()
				currentwordpos += 1
		else:
			elements = line.strip().split("\t")
			currentword = elements[0]
			currentwordfeatures.update(elements[1].split(" "))
		line = analysisfile.readline()
	return analysis


def sanityCheck(translationString, analysis):
	for key in analysis:
		if key not in translationString:
			print("Analyzed word {} not found in original string: {}".format(key, translationString.strip()))


def readSentencePair(translationfile, analysisfile, infofile):
	currenttask, currentexno = "", ""
	currentsentences = []
	currentanalyses = []
	for transline, infoline in zip(translationfile, infofile):
		task, exno = infoline.strip().rsplit(":", 1)
		exno = exno.split(".")[0]
		analysis = readAnalysis(analysisfile)
		sanityCheck(transline, analysis)
		if task == currenttask and exno == currentexno:
			currentsentences.append(transline.strip())
			currentanalyses.append(analysis)
		else:
			if len(currentsentences) > 0:
				yield currentsentences, currentanalyses, currenttask, currentexno
			currenttask = task
			currentexno = exno
			currentsentences = [transline.strip()]
			currentanalyses = [analysis]
	if len(currentsentences) > 0:
		yield currentsentences, currentanalyses, currenttask, currentexno


def worddiff(analysis1, analysis2):
	words_only1 = {w: analysis1[w] for w in analysis1 if w not in analysis2}
	words_only2 = {w: analysis2[w] for w in analysis2 if w not in analysis1}
	return words_only1, words_only2


def worddict2str(worddict):
	posdict = {}
	for w in worddict:
		pos = [int(f[1:]) for f in worddict[w] if f.startswith("@")][0]
		posdict[pos] = w
	s = " ".join([posdict[x] for x in sorted(posdict)])
	return s

def isUnknown(worddict):
	return len(worddict) == 2		# the word itself and its position


# simple feature difference tasks

def sing_plur(wo1, wo2):
	foundSg = any(['Sg' in wo1[x] for x in wo1])	# first sentence should contain singular
	foundPl = any(['Pl' in wo2[x] for x in wo2])	# second sentence should contain plural
	return foundSg, foundPl, ""

def pron_sing_plur(wo1, wo2):
	foundSg = any(['Sg' in wo1[x] for x in wo1])	# first sentence should contain singular
	foundPl = any(['Pl' in wo2[x] for x in wo2])	# second sentence should contain plural
	return foundSg, foundPl, ""

def pres_past(wo1, wo2):
	foundPrs = any(['Prs' in wo1[x] for x in wo1])
	foundPst = any(['Pst' in wo2[x] for x in wo2])
	return foundPrs, foundPst, ""

def comp_adj(wo1, wo2):
	foundPos = any(['Pos' in wo1[x] for x in wo1])
	foundComp = any(['Comp' in wo2[x] for x in wo2])
	return foundPos, foundComp, ""

# doesn't work well if there is more than one negation per sentence
# check again with newly extracted sentences
def pos_neg(wo1, wo2):
	foundPos = not any(['Neg' in wo1[x] for x in wo1])
	foundNeg = any(['Neg' in wo2[x] for x in wo2]) and (any(['ConNeg' in wo2[x] for x in wo2]) or any(['olla' in wo1[x] for x in wo1]))
	# last condition: he ovat tehneet => he eivät tehneet => tehneet does not show up in the second sentence
	return foundPos, foundNeg, ""

# doesn't work well when pronouns are attached as clitics to prepositions
# check again with newly extracted sentences
def human_nonhuman_pron(wo1, wo2):
	foundHuman = any(['hän' in wo1[x] for x in wo1]) or any(['minä' in wo1[x] for x in wo1]) or any(['me' in wo1[x] for x in wo1])
	foundNonhuman = any(['se' in wo2[x] for x in wo2]) or any(['ne' in wo2[x] for x in wo2])
	return foundHuman, foundNonhuman, ""

# check manually - may need to add proper possessive determiners
def det_poss(wo1, wo2):
	foundDet = True		# put a condition here?
	foundPoss = any(['PxSg1' in wo2[x] for x in wo2]) or any(['PxSg2' in wo2[x] for x in wo2]) or any(['Px3' in wo2[x] for x in wo2]) or any(['PxPl1' in wo2[x] for x in wo2]) or any(['PxPl2' in wo2[x] for x in wo2])
	return foundDet, foundPoss, ""

# do we need to check more? position of the verb? morph features of the verb? what about 'jos'? how do the -va forms work?
def that_if(wo1, wo2):
	foundThat = any(['että' in wo1[x] for x in wo1]) or any(['ettei' in wo1[x] for x in wo1]) or any(['PrsPrc' in wo1[x] for x in wo1])
	foundIf = any(['Foc_kO' in wo2[x] for x in wo2])
	return foundThat, foundIf, ""

# replacement tasks

def numbers(wo1, wo2, repl1, repl2):
	found1 = any([repl1 in x for x in wo1.keys()])
	found2 = any([repl2 in x for x in wo2.keys()])
	return found1, found2, ""

def complex_np(wo1, wo2, repl1, repl2):
	foundPron = any(['Pron' in wo1[x] for x in wo1]) or any(['Px3' in wo1[x] for x in wo1])
	for x in wo2:
		if isUnknown(wo2[x]):
			return None

	nouns = [wo2[x] for x in wo2 if 'N' in wo2[x]]
	adjs = [wo2[x] for x in wo2 if 'A' in wo2[x] or 'Qnt' in wo2[x] or 'Ord' in wo2[x] or any(['vuotias' in f for f in wo2[x]])]
	nounFeatures = set()
	adjFeatures = set()
	for n in nouns:
		nounFeatures.update(n)
	for a in adjs:
		adjFeatures.update(a)

	shared = set(nounFeatures) & set(adjFeatures)
	sharedNum = set(['Sg', 'Pl']) & shared
	sharedCase = set(['Nom', 'Par', 'Gen', 'Ine', 'Ela', 'Ill', 'Ade', 'Abl', 'All', 'Ess', 'Ins', 'Abe', 'Tra', 'Com', 'Lat', 'Acc']) & shared
	sameFeatures = len(sharedNum) > 0 and len(sharedCase) > 0
	if sameFeatures:
		return foundPron, len(sharedNum) > 0 and len(sharedCase) > 0, "adj + noun"
	
	compoundNoun = any(["#" in f for f in nounFeatures])	# adj+noun is translated into a compound noun
	if compoundNoun:
		return foundPron, compoundNoun, "compound noun"

	if len(nouns) > 1:
		snouns = sorted(nouns, key=lambda x: [int(n[1:]) for n in x if n.startswith("@")][0])
		foundGen = any(['Gen' in n for n in snouns[:-1]])
		return foundPron, foundGen, "genitive apposition"

	return foundPron, False, ""


# do we need to check more, e.g. case consistency?
def named_entities(wo1, wo2, repl1, repl2):
	s1 = worddict2str(wo1)
	s2 = worddict2str(wo2)
	if " " in repl1 or " " in repl2:
		repl1list = repl1.split(" ")
		repl2list = repl2.split(" ")
		repl1list = [x for x in repl1list if x not in repl2list]
		repl2list = [x for x in repl2list if x not in repl1list]
		repl1 = " ".join(repl1list)
		repl2 = " ".join(repl2list)

	# need to check lemmas also, not only word forms (e.g. Itävalta => Itävallan)
	found1 = repl1.lower() in s2.lower() or nelex.get(repl1, repl1).lower() in s1.lower()
	found2 = repl2.lower() in s2.lower() or nelex.get(repl2, repl2).lower() in s2.lower()
	return found1, found2, ""


def prep1_prep2(wo1, wo2, config1, config2):
	prep1OK = False
	msg = ""
	prep1 = [wo1[x] for x in wo1 if config1[0] in wo1[x]]
	if len(prep1) > 0:
		prep1 = prep1[0]	# there should only be one
		prep1Pos = [int(n[1:]) for n in prep1 if n.startswith("@")][0]
		prep1Nouns = [wo1[x] for x in wo1 if 'N' in wo1[x] or 'Prep' in wo1[x]]
		if config1[2] == 'Prep':
			prep1Nouns = [x for x in prep1Nouns if any([int(n[1:]) > prep1Pos for n in x if n.startswith("@")])]
		else:
			prep1Nouns = [x for x in prep1Nouns if any([int(n[1:]) < prep1Pos for n in x if n.startswith("@")])]

		if len(prep1Nouns) > 0:
			prep1Case = any([config1[3] in x for x in prep1Nouns])
			if not prep1Case:
				msg += "no {} case found with {} ".format(config1[3], config1[1])
			prep1OK = prep1Case
		else:
			msg += "no nouns found with {} ".format(config1[1])
	else:
		msg += "no adposition found with {} ".format(config1[1])

	prep2OK = False
	prep2 = [wo2[x] for x in wo2 if config2[0] in wo2[x]]
	if len(prep2) > 0:
		prep2 = prep2[0]	# there should only be one
		prep2Pos = [int(n[1:]) for n in prep2 if n.startswith("@")][0]
		prep2Nouns = [wo2[x] for x in wo2 if 'N' in wo2[x] or 'Pron' in wo2[x]]
		if config2[2] == 'Prep':
			prep2Nouns = [x for x in prep2Nouns if any([int(n[1:]) > prep2Pos for n in x if n.startswith("@")])]
		else:
			prep2Nouns = [x for x in prep2Nouns if any([int(n[1:]) < prep2Pos for n in x if n.startswith("@")])]

		if len(prep2Nouns) > 0:
			prep2Case = any([config2[3] in x for x in prep2Nouns])
			if not prep2Case:
				msg += "no {} case found with {} ".format(config2[3], config2[1])
			prep2OK = prep2Case
		else:
			msg += "no nouns found {} ".format(config2[1])
	else:
		msg += "no adposition found {} ".format(config2[1])
	return prep1OK, prep2OK, msg


def during_before(wo1, wo2):
	return prep1_prep2(wo1, wo2, ('aikana', 'during', 'Postp', 'Gen'), ('ennen', 'before', 'Prep', 'Par'))

def before_after(wo1, wo2):
	return prep1_prep2(wo1, wo2, ('ennen', 'before', 'Prep', 'Par'), ('jälkeen', 'after', 'Postp', 'Gen'))

def without_with(wo1, wo2):
	return prep1_prep2(wo1, wo2, ('ilman', 'without', 'Prep', 'Par'), ('kanssa', 'with', 'Postp', 'Gen'))


# identity tasks

def masc_fem_pron(wo1, wo2):
	return len(wo1) == 0, len(wo2) == 0, ""

def pres_fut(wo1, wo2):
	if len(wo2) > 0 and any(['tulla' in wo2[x] for x in wo2]):
		return True, True, "tulla"
	return len(wo1) == 0, len(wo2) == 0, ""

def the_a(wo1, wo2):
	return len(wo1) == 0, len(wo2) == 0, ""

def local_prep(wo1, wo2, repl1, repl2):
	localcases = set(['Ess', 'Ine', 'Ela', 'Ill', 'Ade', 'Abl', 'All', 'Par'])
	msg = []
	
	cases1 = set()
	for x in wo1:
		if repl1 == 'behind':
			if 'taka' in wo1[x]:
				cases1.update(wo1[x] & localcases)
			if 'taakse' in wo1[x]:
				cases1.add('Ill')
		
		elif repl1 == 'above':
			if 'ylä#puoli' in wo1[x]:
				cases1.update(wo1[x] & localcases)
			if 'yli' in wo1[x]:
				cases1.add('All'); cases1.add('Ade')
		
		elif repl1 == 'underneath':
			if 'alle' in wo1[x]:
				cases1.add('All')
			if 'alla' in wo1[x]:
				cases1.add('Ade')
			if 'alta' in wo1[x]:
				cases1.add('Abl')
	
	cases2 = set()
	for x in wo2:
		if repl2 == 'in_front_of':
			if 'edessä' in wo2[x]:
				cases2.add('Ine')
			if 'eteen' in wo2[x]:
				cases2.add('Ill')
			if 'edestä' in wo2[x]:
				cases2.add('Ela')
		
		elif repl2 == 'below':
			if 'ala#puoli' in wo2[x]:
				cases2.update(wo2[x] & localcases)
			if 'alle' in wo2[x]:
				cases2.add('All')
			if 'alla' in wo2[x]:
				cases2.add('Ade')
			if 'alta' in wo2[x]:
				cases2.add('Abl')
		
		elif repl2 == 'ahead_of':
			if 'edessä' in wo2[x]:
				cases2.add('Ine')
			if 'eteen' in wo2[x]:
				cases2.add('Ill')
			if 'edestä' in wo2[x]:
				cases2.add('Ela')
			if 'ennen' in wo2[x]:
				cases2.add('All'); cases2.add('Ade')	# dummy cases
		
		elif repl2 == 'next_to':
			if 'vieri' in wo2[x]:
				cases2.update(wo2[x] & localcases)
	
	if len(cases1) == 0 and len(cases2) == 0:
		return False, False, "no translation of {} and {} found".format(repl1, repl2)
	elif len(cases1) == 0:
		return False, True, "no translation of {} found".format(repl1)
	elif len(cases2) == 0:
		return True, False, "no translation of {} found".format(repl2)
		
	caseMatch = False
	for case1 in cases1:
		if case1 in cases2:
			caseMatch = True
			break
		elif case1 in ['Ill', 'All'] and (('All' in cases2) or ('Ill' in cases2)):
			caseMatch = True
			break
		elif case1 in ['Ade', 'Ine', 'Ess'] and (('Ade' in cases2) or ('Ine' in cases2) or ('Ess' in cases2)):
			caseMatch = True
			break
		elif case1 in ['Ela', 'All', 'Par'] and (('All' in cases2) or ('Ela' in cases2) or ('Par' in cases2)):
			caseMatch = True
			break
	
	if not caseMatch:
		return False, False, "no case match"
	else:
		return True, True, ""

####


def format_worddict(worddict):
	posdict = {}
	for w in worddict:
		pos = [int(f[1:]) for f in worddict[w] if f.startswith("@")][0]
		posdict[pos] = worddict[w]
	s = []
	for x in sorted(posdict):
		s.append(" ".join(sorted(posdict[x])))
	return " || ".join(s)


def evaluate(translationfile, analysesfile, infofile, features=None):
	total = collections.defaultdict(int)
	correct = collections.defaultdict(int)
	for sentences, analyses, task, exno in readSentencePair(translationfile, analysesfile, infofile):
		words_only1, words_only2 = worddiff(analyses[0], analyses[1])
		if ":" in task:
			taskname, repl1, repl2 = task.split(":")
		else:
			taskname = task
			repl1, repl2 = "", ""

		if features is not None and taskname not in features.split(" "):
			continue
		
		if taskname in globals():
			taskproc = globals()[taskname]
			
			if repl1 == "":
				result = taskproc(words_only1, words_only2)
			else:
				result = taskproc(words_only1, words_only2, repl1, repl2)
			
			if result is None:
				print("\t".join([task, exno, "Unknown word", sentences[0], format_worddict(words_only1), sentences[1], format_worddict(words_only2)]))
				continue
			
			x, y, msg = result
			if x and y:		# both features found => correct
				correct[taskname] += 1
				total[taskname] += 1

			elif len(words_only1) == 0 and len(words_only2) == 0:
				# identical
				total[taskname] += 1
			
			elif x or y:	# only one feature found => wrong
				if not x:
					msg2 = "Left feature not found"
					if msg != "":
						msg2 += ": " + msg
					print("\t".join([task, exno, msg2, sentences[0], format_worddict(words_only1), sentences[1], ""]))
				if not y:
					msg2 = "Right feature not found"
					if msg != "":
						msg2 += ": " + msg
					print("\t".join([task, exno, msg2, sentences[0], "", sentences[1], format_worddict(words_only2)]))
				total[taskname] += 1
			
			else:
				msg2 = "Both features not found"
				if msg != "":
					msg2 += ": " + msg
				print("\t".join([task, exno, msg2, sentences[0], format_worddict(words_only1), sentences[1], format_worddict(words_only2)]))
				total[taskname] += 1
	
	print()
	print("\t".join(["Task", "Correct", "Total", "Accuracy"]))
	for task in sorted(total):
		print("\t".join([task, "{}".format(correct.get(task, 0)), "{}".format(total[task]), "{:.2f}%".format(100 * correct.get(task, 0) / total[task])]))


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-trans', dest='trans', nargs="?", type=argparse.FileType('r'), help="translated input sentences")
	parser.add_argument('-morph', dest='morph', nargs="?", type=argparse.FileType('r'), help="hfst-analyzed input sentences")
	parser.add_argument('-info', dest='info', nargs="?", type=argparse.FileType('r'), help="input info file")
	parser.add_argument('-feats', dest='feats', nargs="?", help="list of features to analyze")
	args = parser.parse_args()
	
	evaluate(args.trans, args.morph, args.info, args.feats)

