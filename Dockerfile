FROM openjdk:11-slim

RUN apt update && apt install -y python3 latexmk texlive-latex-extra python3-pip

RUN pip3 install requests

RUN useradd -m timesheet_generator

RUN chown -R timesheet_generator:timesheet_generator /home/timesheet_generator

COPY TimeSheetGenerator/Generator.jar /home/timesheet_generator/TimesheetGenerator/
COPY TimeSheetGenerator/Latex_Logo.pdf /home/timesheet_generator/TimesheetGenerator/
COPY TimesheetGenerator.py /home/timesheet_generator

# Drop privs
USER timesheet_generator

ENTRYPOINT ["/usr/bin/python3", "/home/timesheet_generator/TimesheetGenerator.py", "/home/timesheet_generator/TimesheetGenerator"]
