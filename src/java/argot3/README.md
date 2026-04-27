# Argot3

Argot3 (Annotation Retrieval of Gene Ontology Terms) is a new version of 
[Argot2.5](https://pubmed.ncbi.nlm.nih.gov/26318087/) where the output data are not filtered.

## Requirements

- Java 17
- Maven (for building)

## Dependencies

To correctly run Argot3, the libraries in the 
[java_libraries](https://gitlab.com/medcomp/libraries_scripts/java_libraries/-/tree/master/argot_domains_functionalspace) 
repository must be installed, or Maven must be used as described below.

## Building the JAR file

To build the JAR file, you can use an IDE ([NetBeans](https://netbeans.apache.org/) or 
[IntelliJ IDEA](https://www.jetbrains.com/idea/)) or Maven via terminal.

From the project root:

mvn install:install-file -Dfile=./lib/jgrapht-bundle-1.3.0.jar -DgroupId=org.jgrapht -DartifactId=jgrapht-bundle -Dversion=1.3.0 -Dpackaging=jar

mvn install:install-file -Dfile=./lib/goUtility-4.0.jar -DgroupId=it.unipd.medicina.medcomp -DartifactId=goUtility -Dversion=4.0 -Dpackaging=jar

mvn clean install

The JAR file will be created in the `target/` directory.

## Running

java -jar target/Argot3-1.0.jar [options]