from rdflib import Graph
import sys,os
import argparse
import graphviz


##################
# USR CFG & INIT #
##################

args=argparse.ArgumentParser(description="given the URL of an RDF file, extract and serialize the data model, limited to RDFS semantics")
args.add_argument("src", type=str, help="URL of the source file")
args.add_argument("-r", "--include_relations", action="store_true", help="if set, also plot domain and range declarations")
args=args.parse_args()

##########
# CONFIG #
##########

# where to find SPARQL updates
RDFS_UPD="sparql/rdfs-inference.sparql"

# where to find SPARQL queries
CLASS_Q="sparql/classes.sparql"
INST_Q="sparql/instances.sparql"
PROPS_Q="sparql/properties.sparql"
SUBPROPS_Q="sparql/subproperties.sparql"

#######################
# load SPARQL scripts #
#######################

with open(RDFS_UPD,"rt") as input:
	RDFS_UPD=input.read()

with open(CLASS_Q,"rt") as input:
	CLASS_Q=input.read()

with open(INST_Q,"rt") as input:
	INST_Q=input.read()

with open(PROPS_Q,"rt") as input:
	PROPS_Q=input.read()

with open(SUBPROPS_Q,"rt") as input:
	SUBPROPS_Q=input.read()

########
# init #
########

g = Graph().parse(args.src)
g_len=0
while(g_len<len(g)):
	g_len=len(g)
	g.update(RDFS_UPD)
	if len(g)-g_len > 0:
		sys.stderr.write(f"prep: inferred {len(g)-g_len} triples\n")
		sys.stderr.flush()

##############
# extraction #
##############

def escape(label):
	""" escape labels to get valid GraphViz/Dot node IDs """
	reserved_symbols="/:"
	for s in reserved_symbols:
		label="_".join(label.split(s))
	return label

def get_label(label):
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

def add_path_to_dict(d, path):
	if not isinstance(d,dict): d={}
	if len(path)>0:
		newd={}
		if path[0] in d:
			newd=d[path[0]]
		d[path[0]]=add_path_to_dict(newd,path[1:])
	return d

def prop_dict_to_labels(d):
	leaves=[]
	nodes=[]
	for key in d:
		if d[key]=={}:
			leaves.append(key)
		else:
			nodes+=[ key+"\n└─ "+label for label in prop_dict_to_labels(d[key])]

	if len(leaves)>0:
		result=None
		for l in leaves:
			if result:
				result+=", "
			else:
				result=""
			if len(result.split("\n")[-1])>50: 
				result+="\n" 
			result+=l
		nodes=sorted(nodes+[result])

	return nodes

dot = graphviz.Digraph(graph_attr={"rankdir":"LR"}) #, "splines":"ortho"}) # {"rotate":"90"})

class2label={}

for nr,(cl,parent) in enumerate(g.query(CLASS_Q)):
	#if(nr>=10):
	#	break
	cl=get_short_name(cl)
	parent=get_short_name(parent)
	if not cl in class2label:
		class2label[cl]=get_label(cl)
	if parent!=None:
		dot.edge(escape(parent),escape(cl),dir="back",arrowtail="empty")
		if not parent in class2label:
			class2label[parent]=get_label(parent)

prop2super={}
src2tgt2props={}
src_props=set()
tgt_props=set()

if args.include_relations:
	for nr,(prop,sprop) in enumerate(g.query(SUBPROPS_Q)):
		if not prop in prop2super:
			prop2super[prop]=sprop
		elif prop2super[prop]!=sprop:
			sys.stderr.write(f"""warning: we currently support one super property per property only.
				using {prop2super[prop]} for {prop}, skipping {sprop}.\n""")
			sys.stderr.flush()

	props_result=g.query(PROPS_Q)

	for nr,(dom,prop,ran) in enumerate(props_result):
		if dom!=None and not prop in src_props: 
			src_props.add(prop)
			print(f"{prop} has dom {dom}")
		if ran!=None and not prop in tgt_props: 
			tgt_props.add(prop)
			print(f"{prop} has ran {ran}")

	for nr,(dom,prop,ran) in enumerate(props_result):
		if prop and not prop in prop2super.values():
			if dom or not prop in src_props:
				if ran or not prop in tgt_props:
					label=get_short_name(prop)
					if label.strip()!="":
						path=[label]
						while(prop in prop2super):
							prop=prop2super[prop]
							label=get_short_name(prop)
							path=[label]+path
						if not dom in src2tgt2props: src2tgt2props[dom]={}
						if not ran in src2tgt2props[dom]: src2tgt2props[dom][ran]={}
						src2tgt2props[dom][ran]=add_path_to_dict(src2tgt2props[dom][ran], path)
	print(src2tgt2props)

#print("ADDED",src2tgt2props.keys(), [ src2tgt2props[k].keys() for k in src2tgt2props.keys() ])

cl2inst={}

for nr,(inst,cl) in enumerate(g.query(INST_Q)):
	cl=get_short_name(cl)
	if not cl in class2label:
		class2label[cl]=get_label(cl)

	inst=get_short_name(inst)
	if( not cl in cl2inst):
		cl2inst[cl]=set([])
	cl2inst[cl].add(inst)

####################
# write properties #
####################

from pprint import pprint
pprint(src2tgt2props)

print("CHECK src_props:",sorted(src_props))
print("CHECK tgt_props:",sorted(tgt_props))

for src in src2tgt2props:
	for tgt in src2tgt2props[src]:
		for prop in src2tgt2props[src][tgt]:
			
					label="\n\n".join(prop_dict_to_labels(src2tgt2props[src][tgt]))
					if "\n\n" in label:
						label="\n\n\n"+label
				
					print("EDGE:",src,tgt,label)

					dom=None
					ran=None
					if src==None and tgt==None:
						dom="anyURI"
						ran="..."
						class2label[dom]="anyURI"
						class2label[ran]="..."
					elif src==None:
						ran=get_short_name(tgt)
						dom="dom_"+ran
						class2label[dom]="anyURI"
					elif tgt==None:
						dom=get_short_name(src)
						ran="ran_"+dom
						class2label[ran]="..."
					else:
						dom=get_short_name(src)
						ran=get_short_name(tgt)

					dot.edge(escape(dom),escape(ran),label=label)
					break # don't draw it multiple times

#################
# write classes #
#################

for cl,label in class2label.items():
	dot.node(escape(cl),label=label,shape="box")

###################
# write instances #
###################

for nr,(cl,i) in enumerate(cl2inst.items()):
	label=[]
	for n,l in enumerate(sorted(i)):
		if n>0 and n % 3 == 0:
			l="\n"+l
		label.append(l)
	label=",".join(label)

	i=f"i_{nr}"
	dot.node(i,label=label,shape="none")
	dot.edge(escape(cl),i,dir="back",arrowtail="none",arrowhead="none")

#help(dot)
dot.render(format="pdf")