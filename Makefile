all: pdf

pdf: data
	if [ ! -e pdf ]; then mkdir pdf; fi;
	for file in data/*.ttl; do \
		tgt=pdf/`basename $$file`.pdf;\
		scaled=pdf/`basename $$file`.poster.pdf;\
		if [ ! -e $$tgt ]; then \
			python3 rdfs2dot.py -r $$file;\
			mv Digraph.gv.pdf $$tgt;\
			if [ ! -e $$scaled ]; then \
				pdfposter $$tgt -s 0.1625  $$scaled;\
			fi;\
		fi;\
	done;\

data: data/lexinfo.ttl

data/lexinfo.ttl:
	if [ ! - e data ]; then mkdir data; fi;
	cd data; \
	wget -nc https://lexinfo.net/ontology/3.0/lexinfo.ttl

