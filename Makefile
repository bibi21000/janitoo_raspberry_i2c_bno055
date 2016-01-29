# Makefile for janitoo
#

# You can set these variables from the command line.
ARCHBASE      = archive
BUILDDIR      = build
DISTDIR       = dists
NOSE          = $(shell which nosetests)
NOSEOPTS      = --verbosity=2
PYLINT        = $(shell which pylint)
PYLINTOPTS    = --max-line-length=140 --max-args=9 --extension-pkg-whitelist=zmq --ignored-classes=zmq --min-public-methods=0

ifndef PYTHON_EXEC
PYTHON_EXEC=python
endif

ifndef message
message="Auto-commit"
endif

ifdef VIRTUAL_ENV
python_version_full := $(wordlist 2,4,$(subst ., ,$(shell ${VIRTUAL_ENV}/bin/${PYTHON_EXEC} --version 2>&1)))
else
python_version_full := $(wordlist 2,4,$(subst ., ,$(shell ${PYTHON_EXEC} --version 2>&1)))
endif

janitoo_version := $(shell ${PYTHON_EXEC} _version.py)

python_version_major = $(word 1,${python_version_full})
python_version_minor = $(word 2,${python_version_full})
python_version_patch = $(word 3,${python_version_full})

PIP_EXEC=pip
ifeq (${python_version_major},3)
	PIP_EXEC=pip3
endif

MODULENAME   = $(shell basename `pwd`)

NOSECOVER     = --cover-package=janitoo,janitoo_db,${MODULENAME} --with-coverage --cover-inclusive --cover-tests --cover-html --cover-html-dir=${BUILDDIR}/docs/html/tools/coverage --with-html --html-file=${BUILDDIR}/docs/html/tools/nosetests/index.html

DEBIANDEPS := $(shell [ -f debian.deps ] && cat debian.deps)
BASHDEPS := $(shell [ -f bash.deps ] && echo "bash.deps")
JANITOODEPS := $(shell [ -f janitoo.deps ] && echo janitoo.deps)
BOWERDEPS := $(shell [ -f bower.deps ] && cat bower.deps)

TAGGED := $(shell git tag | grep -c v${janitoo_version} )

-include Makefile.local

.PHONY: help check-tag clean all build develop install uninstall clean-doc doc certification tests pylint deps

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  build           : build the module"
	@echo "  develop         : install for developpers"
	@echo "  install         : install for users"
	@echo "  uninstall       : uninstall the module"
	@echo "  deps            : install dependencies for users"
	@echo "  doc   	    	 : make documentation"
	@echo "  tests           : launch tests"
	@echo "  clean           : clean the development directory"

clean-dist:
	-rm -rf $(DISTDIR)

clean: clean-doc
	-rm -rf $(ARCHBASE)
	-rm -rf $(BUILDDIR)
	-rm -f generated_doc
	-rm -f janidoc
	-@find . -name \*.pyc -delete

uninstall:
	-yes | ${PIP_EXEC} uninstall ${MODULENAME}
	-${PYTHON_EXEC} setup.py develop --uninstall
	-yes | ${PIP_EXEC} uninstall ${MODULENAME}
	-${PYTHON_EXEC} setup.py develop --uninstall
	#~ -@find . -name \*.egg-info -type d -exec rm -rf "{}" \;

deps:
ifneq ('${BASHDEPS}','')
	bash ${BASHDEPS}
endif
ifneq ('${DEBIANDEPS}','')
	sudo apt-get install -y ${DEBIANDEPS}
endif
	@echo
	@echo "Dependencies for ${MODULENAME} finished."

clean-doc:
	-rm -Rf ${BUILDDIR}/docs
	-rm -Rf ${BUILDDIR}/janidoc

janidoc:
	ln -s /opt/janitoo/src/janidoc janidoc

apidoc:
	-rm -rf ${BUILDDIR}/janidoc/source/api
	-rm -rf ${BUILDDIR}/janidoc/source/extensions
	-mkdir -p ${BUILDDIR}/janidoc/source/api
	-mkdir -p ${BUILDDIR}/janidoc/source/extensions
	cp -Rf janidoc/* ${BUILDDIR}/janidoc/
	cd ${BUILDDIR}/janidoc/source/api && sphinx-apidoc --force --no-toc -o . ../../../../src/
	cd ${BUILDDIR}/janidoc/source/api && mv ${MODULENAME}.rst index.rst
	cd ${BUILDDIR}/janidoc/source && ./janitoo_collect.py  >extensions/index.rst

doc: janidoc apidoc
	- [ -f transitions_graph.py ] && python transitions_graph.py
	-cp -Rf rst/* ${BUILDDIR}/janidoc/source
	make -C ${BUILDDIR}/janidoc html
	cp ${BUILDDIR}/janidoc/source/README.rst README.rst
	-ln -s $(BUILDDIR)/docs/html generated_doc
	@echo
	@echo "Documentation finished."

pylint:
	-mkdir -p ${BUILDDIR}/docs/html/tools/pylint
	$(PYLINT) --output-format=html $(PYLINTOPTS) src/${MODULENAME} >${BUILDDIR}/docs/html/tools/pylint/index.html

install:
	${PYTHON_EXEC} setup.py install
	@echo
	@echo "Installation of ${MODULENAME} finished."

develop:
	-${PYTHON_EXEC} setup.py develop
	@echo
	@echo "Installation for developpers of ${MODULENAME} finished."

docker-deps:
	@echo
	@echo "Docker dependencies for ${MODULENAME} installed."

travis-deps:
	sudo apt-get install -y python-pip
	git clone https://github.com/bibi21000/janitoo_mosquitto.git
	make -C janitoo_mosquitto deps
	make -C janitoo_mosquitto develop
	sudo mkdir /opt/janitoo
	sudo chown -Rf ${USER}:${USER} /opt/janitoo
	for dir in src cache cache/janitoo_manager home log run etc init; do mkdir /opt/janitoo/$$dir; done
	pip install git+git://github.com/bibi21000/janitoo_nosetests@master
	pip install git+git://github.com/bibi21000/janitoo_nosetests_flask@master
	pip install coveralls
	@echo
	@echo "Travis dependencies for ${MODULENAME} installed."

tests:
	-mkdir -p ${BUILDDIR}/docs/html/tools/coverage
	-mkdir -p ${BUILDDIR}/docs/html/tools/nosetests
	#~ export NOSESKIP=False && $(NOSE) $(NOSEOPTS) $(NOSECOVER) tests ; unset NOSESKIP
	$(NOSE) $(NOSEOPTS) $(NOSECOVER) tests
	@echo
	@echo "Tests for ${MODULENAME} finished."

certification:
	$(NOSE) --verbosity=2 --with-xunit --xunit-file=certification/result.xml certification
	@echo
	@echo "Certification for ${MODULENAME} finished."

build:
	${PYTHON_EXEC} setup.py build --build-base $(BUILDDIR)

egg:
	-mkdir -p $(BUILDDIR)
	-mkdir -p $(DISTDIR)
	${PYTHON_EXEC} setup.py bdist_egg --bdist-dir $(BUILDDIR) --dist-dir $(DISTDIR)

tar:
	-mkdir -p $(DISTDIR)
	tar cvjf $(DISTDIR)/${MODULENAME}-${janitoo_version}.tar.bz2 -h --exclude=\*.pyc --exclude=\*.egg-info --exclude=janidoc --exclude=.git* --exclude=$(BUILDDIR) --exclude=$(DISTDIR) --exclude=$(ARCHBASE) .
	@echo
	@echo "Archive for ${MODULENAME} version ${janitoo_version} created"

commit: develop
	-git add rst/
	-cp rst/README.rst .
	-git add README.rst
	-git commit -m "$(message)" -a
	git push
	@echo
	@echo "Commits for branch master pushed on github."

pull:
	git pull
	@echo
	@echo "Commits from branch master pulled from github."

status:
	git status

tag: check-tag commit
	git tag v${janitoo_version}
	git push origin v${janitoo_version}
	@echo
	@echo "Tag pushed on github."

check-tag:
ifneq ('${TAGGED}','0')
	echo "Already tagged with version ${janitoo_version}"
	@/bin/false
endif

new-version: tag clean tar
	@echo
	@echo "New version ${janitoo_version} created and published"

debch:
	dch --newversion ${janitoo_version} --maintmaint "Automatic release from upstream"

deb:
	dpkg-buildpackage
