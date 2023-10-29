
import csv
import logging
import sys

logging.basicConfig(level=logging.DEBUG, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()


def read_shownotes(filename='../show-notes-export.csv') -> list:
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        rc = []  # Array of dicts
        for record in reader:
            rc.append(record)
        log.info(f"{len(rc)} records found in {filename}")
        return rc


if __name__ == '__main__':
    if len(sys.argv) > 1:
        rc = read_shownotes(filename=sys.argv[1])
    else:
        rc = read_shownotes()

    log.info('Exporting to markdown...')
    with open('../show-notes-export.md', 'w') as mdfile:
        mdfile.write('### Episode links\n')
        for rec in rc:
            record = f"- [{rec['Title']}]({rec['Destination']}) [Source]({rec['Source']})\n"
            mdfile.write(record)
