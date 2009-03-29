import subprocess
import time
import sys


def main():
    process = subprocess.Popen("wmiir read /event", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    while True:
        data = process.stdout.readline().split()
        if data[0] == 'ClientFocus':
            cliname = subprocess.Popen("wmiir read /client/%s/label" % data[1], stdout=subprocess.PIPE, shell=True).stdout.read()
            print ("Client: %s" % cliname)

        print data

if __name__ == '__main__':
    main()
