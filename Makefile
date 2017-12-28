# Makefile for janitoo
#

include Makefile.janitoo
-include Makefile.local

.PHONY: help check-tag clean all build develop install uninstall clean-doc doc certification tests pylint deps docker-tests

clean-dist:
	-rm -rf $(DISTDIR)

clean: clean-doc
	-rm -rf $(ARCHBASE)
	-rm -rf $(BUILDDIR)
	-rm -f .coverage
	-@find . -name \*.pyc -delete

uninstall:
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

install:
	${PYTHON_EXEC} setup.py install
	@echo
	@echo "Installation of ${MODULENAME} finished."

develop:
	-${PYTHON_EXEC} setup.py develop
	@echo
	@echo "Installation for developpers of ${MODULENAME} finished."

docker-deps:
	-cp -rf docker/config/* /opt/janitoo/etc/
	-cp -rf docker/supervisor.conf.d/* /etc/supervisor/janitoo.conf.d/
	-cp -rf docker/supervisor-tests.conf.d/* /etc/supervisor/janitoo-tests.conf.d/
	-cp -rf docker/nginx/* /etc/nginx/conf.d/
	true
	@echo
	@echo "Docker dependencies for ${MODULENAME} installed."

appliance-deps:
	-cp -rf docker/appliance/* /opt/janitoo/etc/
	-cp -rf docker/supervisor.conf.d/* /etc/supervisor/janitoo.conf.d/
	-cp -rf docker/nginx/* /etc/nginx/conf.d/
	@echo
	@echo "Appliance dependencies for ${MODULENAME} installed."

directories:
	-sudo mkdir /opt/janitoo
	-sudo chown -Rf ${USER}:${USER} /opt/janitoo
	-for dir in cache cache/janitoo_manager home log run etc init; do mkdir /opt/janitoo/$$dir; done

travis-deps:
	sudo apt-get install -y python-pip
	git clone https://github.com/bibi21000/janitoo_mosquitto.git
	make -C janitoo_mosquitto deps
	make -C janitoo_mosquitto develop
	pip install git+git://github.com/bibi21000/janitoo_nosetests@master
	pip install git+git://github.com/bibi21000/janitoo_nosetests_flask@master
	pip install smbus-cffi
	pip install coveralls
	@echo
	@echo "Travis dependencies for ${MODULENAME} installed."

docker-tests:
	@echo
	@echo "Docker tests for ${MODULENAME} start."
	[ -f tests/test_docker.py ] && $(NOSE) $(NOSEOPTS) $(NOSEDOCKER) tests/test_docker.py
	@echo
	@echo "Docker tests for ${MODULENAME} finished."

docker-local-pull:
	@echo
	@echo "Pull local docker for ${MODULENAME}."
	docker pull bibi21000/${MODULENAME}
	@echo
	@echo "Docker local for ${MODULENAME} pulled."

docker-local-store: docker-local-pull
	@echo
	@echo "Create docker local store for ${MODULENAME}."
	docker create -v /root/.ssh/ -v /opt/janitoo/etc/ ${DOCKERVOLS} --name ${DOCKERNAME}_store bibi21000/${MODULENAME} /bin/true
	@echo
	@echo "Docker local store for ${MODULENAME} created."

docker-local-running: docker-local-pull
	@echo
	@echo "Update local docker for ${MODULENAME}."
	-docker stop ${DOCKERNAME}_running
	-docker rm ${DOCKERNAME}_running
	docker create --volumes-from ${DOCKERNAME}_store -p ${DOCKERPORT}:22 --name ${DOCKERNAME}_running bibi21000/${MODULENAME}
	docker ps -a|grep ${DOCKERNAME}_running
	docker start ${DOCKERNAME}_running
	docker ps|grep ${DOCKERNAME}_running
	@echo
	@echo "Docker local for ${MODULENAME} updated."

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

commit:
	-git add rst/
	-cp rst/README.rst .
	-git add README.rst
	git commit -m "$(message)" -a && git push
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
