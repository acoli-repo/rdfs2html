from rdflib import Graph
import sys,os
import argparse
import graphviz


##################
# USR CFG & INIT #
##################

args=argparse.ArgumentParser(description="given the URL of an RDF file, extract and serialize the data model, limited to RDFS semantics")
args.add_argument("src", type=str, help="URL of the source file")
args=args.parse_args()

g = Graph().parse(args.src)

##########
# CONFIG #
##########

# where to find SPARQL queries
CLASS_Q="sparql/classes.sparql"
INST_Q="sparql/instances.sparql"

#######################
# load SPARQL queries #
#######################

with open(CLASS_Q,"rt") as input:
	CLASS_Q=input.read()

with open(INST_Q,"rt") as input:
	INST_Q=input.read()

##############
# extraction #
##############

def escape(label):
	""" escape labels to get valid GraphViz/Dot node IDs """
	reserved_symbols="/:"
	for s in reserved_symbols:
		label="_".join(label.split(s))
	return label

def label(label):
	""" return a label with line break after namespace pfx """
	return ":\n".join(label.split(":"))

def get_short_name(URI_or_string):
	""" return short name. note that we don't use prefixes, but the last term before the last # or / """
	string=str(URI_or_string)
	segs="/".join(string.split("#")).split("/")
	try:
		return segs[-2]+":"+segs[-1]
	except: 
		return ":"+segs[-1]

dot = graphviz.Digraph(graph_attr={"rankdir":"LR"}) #, "splines":"ortho"}) # {"rotate":"90"})

class2label={}

for nr,(cl,parent) in enumerate(g.query(CLASS_Q)):
	#if(nr>=10):
	#	break
	cl=get_short_name(cl)
	parent=get_short_name(parent)
	if not cl in class2label:
		class2label[cl]=label(cl)
	if parent!=None:
		dot.edge(escape(parent),escape(cl),dir="back")
		if not parent in class2label:
			class2label[parent]=label(parent)

cl2inst={}

for nr,(inst,cl) in enumerate(g.query(INST_Q)):
	print(inst,cl)
	cl=get_short_name(cl)
	if not cl in class2label:
		class2label[cl]=label(cl)

	print(inst)
	inst=get_short_name(inst)
	print(inst)
	if( not cl in cl2inst):
		cl2inst[cl]=set([])
	cl2inst[cl].add(inst)
	print(cl2inst[cl])

for nr,(cl,i) in enumerate(cl2inst.items()):
	label=[]
	for n,l in enumerate(sorted(i)):
		if n>0 and n % 3 == 0:
			l="\n"+l
		label.append(l)
	label=",".join(label)

	i=f"i_{nr}"
	dot.node(i,label=label,shape="none")
	dot.edge(escape(cl),i,dir="back")

for cl,label in class2label.items():
	dot.node(escape(cl),label=label,shape="box")

#help(dot)
dot.render(format="pdf")