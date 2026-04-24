FROM maven:3-openjdk-11

ADD ./pom.xml /argot/
ADD ./src/ /argot/src/
ADD ./lib/ /argot/lib/
ADD ./libgraph/ /argot/libgraph/

RUN cd /argot/ \
   && mvn install:install-file -Dfile=/argot/lib/jgrapht-bundle-1.3.0.jar -DgroupId=org.jgrapht -DartifactId=jgrapht-bundle -Dversion=1.3.0 -Dpackaging=jar \
   && mvn install:install-file -Dfile=/argot/lib/goUtility-4.0.jar -DgroupId=it.unipd.medicina.medcomp -DartifactId=goUtility -Dversion=4.0 -Dpackaging=jar \
   && mvn install

ENTRYPOINT ["java", "-jar", "/argot/target/Argot3-1.0.jar"]