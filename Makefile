all: docker

TimeSheetGenerator:
	git clone https://github.com/I-Al-Istannen/TimeSheetGenerator

TimeSheetGenerator/Generator.jar: TimeSheetGenerator
	cd TimeSheetGenerator && mvn clean package
	cp TimeSheetGenerator/target/*-with-dependencies.jar TimeSheetGenerator/Generator.jar

TimeSheetGenerator/Latex_Logo.pdf: TimeSheetGenerator
	cp TimeSheetGenerator/examples/Latex_Logo.pdf TimeSheetGenerator/Latex_Logo.pdf

docker: TimeSheetGenerator/Latex_Logo.pdf TimeSheetGenerator/Generator.jar
	sudo docker build -t timesheet-generator .

clean:
	rm -rf TimeSheetGenerator

.PHONY: clean
