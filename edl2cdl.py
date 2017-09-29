##################################################
##  edl2cdl.py                                  ##
##______________________________________________##
##  Reads a CMX3600-like Edit Decision List     ##
##  (EDL) file, extracts all the CDLs in it,    ##
##  exports either  single Color Decision List  ##
##  (.cdl file extension), a single correction  ##
##  (.cc file extension), or a *Collection* of  ##
##  of color corrections (.ccc file extension)  ##
##  CDLs are then named or given IDs according  ##
##  to the EDL tapenames. Footage coming from   ##
##  ARRI, RED or similar cameras has tapenames  ##
##  like "A001[_]C009[...]" which this utility  ##
##  acknowledges to use "A001C001" as tapename  ##
##  in IDs within the CCC file (or as filename  ##
##  for individual CDLs/CCs within a folder.    ##
##______________________________________________##
##  Copyright (C) 2017 Walter Arrighetti, PhD   ##
##                                              ##
##################################################
#!/usr/bin/env python
_version = "2.0"
import os,re, sys, argparse, errno
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from ElementTree_pretty import prettify

def writeCDL(CCC, IDs, CCCid, SOPnode, SATnode):
    CCC.append({
        'id': CCCid,
        'slope': SOPnode[0],
        'offset': SOPnode[1],
        'power': SOPnode[2],
        'SAT':   SATnode
    })
    IDs.append(CCCid)

def getArgs():
    argEpilog = ("EDL-to-CDL Conversion Utility version %s" % _version ) + "\nCopyright (C) 2017 Walter Arrighetti PhD, Frame by Frame Italia.\n"
    parser = argparse.ArgumentParser(version=_version, prog='edl2cdl.py', epilog=argEpilog)
    parser.add_argument(
        '-i',
        '--input',
        help='Input to CMX3600-like EDL File',
        required=True,
        type=argparse.FileType('rU'))
    parser.add_argument(
        '-o',
        '--output',
        help='Output to File or Folder. Depends Upon Format. If format is "ccc", output must end in ccc. Otherwise, must be a folder.',
        required=True
    )
    parser.add_argument(
        '-f',
        '--format',
        help="Choose between cdl(Color Decision List), cc(Color Correction), ccc(Color Correction Collection). cdl and cc REQUIRE your output to be a folder. ccc is a file.",
        default='cdl',
        choices=['cdl', 'cc', 'ccc']
    )
    parser.add_argument(
        '-e',
        '--event',
        help='Choose between "clip" for "FROM CLIP NAME" or "loc" for Locator Notes defining an edit event. Results in file name for cdl and cc formats.',
        default='clip',
        choices=['clip', 'loc']
    )

    return parser.parse_args()

def cdl1Parse(reMatches):
    return (tuple(map(float, (reMatches.group("sR"), reMatches.group("sG"), reMatches.group("sB")))), tuple(map(float, (reMatches.group(
        "oR"), reMatches.group("oG"), reMatches.group("oB")))), tuple(map(float, (reMatches.group("pR"), reMatches.group("pG"), reMatches.group("pB")))))

def appendCCXML(ccID, slope, offset, power, sat, rootElement = None):
    if rootElement is not None:
        ccElement = SubElement(rootElement, 'ColorCorrection', {'id': ccID})
    else:
        ccElement = Element('ColorCorrection', {'id': ccID})

    sopElement = SubElement(ccElement, 'SOPNode')
    slopeElement = SubElement(sopElement, 'Slope')
    slopeElement.text = "%.05f %.05f %.05f" % slope
    offsetElement = SubElement(sopElement, 'Offset')
    offsetElement.text = "%.05f %.05f %.05f" % offset
    powerElement = SubElement(sopElement, 'Power')
    powerElement.text = "%.05f %.05f %.05f" % power
    satElement = SubElement(ccElement, 'SatNode')
    saturationElement = SubElement(satElement, 'Saturation')
    saturationElement.text = "%.05f" % sat

    return ccElement

def main(argv):
    args = getArgs()

    output = os.path.abspath(args.output)
    edlInput = args.input

    if args.format == 'ccc':
        if output[-3:] != 'ccc':
            raise ValueError('The Output(-o) must be a file that ends in ".ccc" when using the format(-f) "ccc".')
        output_path = os.path.split(output)[0]
        if not os.path.isdir(output_path):
            os.mkdir(output_path)
    else:
        try:
            os.mkdir(output)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

    cdl1re = re.compile(r"\*\s?ASC[_]SOP\s+[(]\s?(?P<sR>[-]?\d+[.]\d{4,6})\s+(?P<sG>[-]?\d+[.]\d{4,6})\s+(?P<sB>[-]?\d+[.]\d{4,6})\s?[)]\s?[(]\s?(?P<oR>[-]?\d+[.]\d{4,6})\s+(?P<oG>[-]?\d+[.]\d{4,6})\s+(?P<oB>[-]?\d+[.]\d{4,6})\s?[)]\s?[(]\s?(?P<pR>[-]?\d+[.]\d{4,6})\s+(?P<pG>[-]?\d+[.]\d{4,6})\s+(?P<pB>[-]?\d+[.]\d{4,6})\s?[)]")
    cdl2re = re.compile(r"\*\s?ASC[_]SAT\s+(?P<sat>\d+[.]\d{4,6})")
    CDLevent = False
    thisCDL = None
    IDs = []
    CCC = []

    if args.event == 'clip':
        camre = re.compile(r"\*\s?FROM\sCLIP\sNAME:\s+.*(?P<name>[A-Z][0-9]{3}[_]?C[0-9]{3})")
        camre0 = re.compile(r"\*\sFROM\sCLIP\sNAME:\s+(?P<name>.{63})")
        camre1 = re.compile(r"[*]\s(?P<name>.*)")
        #Greedier FROM CLIP NAME Regex
        camre3 = re.compile(r"\*\s?FROM\sCLIP\sNAME:\s+(?P<name>[A-Z0-9_\-]+)")
        tapere = re.compile(r"\*\sFROM\sCLIP\sNAME:\s+(?P<name>[A-Za-z0-9-_,.]|\s{8,32})")
        edlLines = edlInput.readlines()
        lenEdlLines = len(edlLines)
        for n in range(lenEdlLines):
            line = edlLines[n].strip()
            if line[0] != '*':
                continue
            if camre.match(line):
                CDLevent, L = True, camre.match(line)
                if thisCDL:
                    writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
                    thisCDL, thisSAT = None, 0
                tapename = L.group("name")
                if tapename in IDs:
                    tapename, CDLevent = None, False
            elif camre0.match(line) and n < lenEdlLines - 1 and camre1.match(edlLines[n + 1]):
                n += 1
                line = line + camre1.match(edlLines[n]).group("name")
                L = camre.match(line)
                if not L:
                    writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
                    thisCDL, thisSAT = None, 0
                else:
                    CDLevent = True
                tapename = L.group("name")
                if tapename in IDs:
                    tapename, CDLevent = None, False
                if thisCDL:
                    thisCDL, thisSAT = None, 0
            elif tapere.match(line):
                CDLevent, L = True, tapere.match(line)
                if thisCDL:
                    writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
                    thisCDL, thisSAT = None, 0
                tapename = L.group("name")
                if tapename in IDs:
                    tapename, CDLevent = None, False
            elif camre3.match(line):
                CDLevent, L = True, camre3.match(line)
                if thisCDL:
                    writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
                    thisCDL, thisSAT = None, 0
                tapename = L.group("name")
                if tapename in IDs:
                    tapename, CDLevent = None, False
            elif CDLevent and cdl1re.match(line):
                L = cdl1re.match(line)
                thisCDL = cdl1Parse(L)
                thisSAT = 0
            elif CDLevent and thisCDL and cdl2re.match(line):
                L = cdl2re.match(line)
                thisSAT = float(L.group("sat"))
                writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
                tapename, CDLevent, thisCDL, thisSAT = None, False, None, 0
    else:
        locRE = re.compile(r'\*\s?LOC:\s+\d\d:\d\d:\d\d:\d\d\s+\w*\s+(?P<name>.*)')
        for line in edlInput.readlines():
            line = line.strip()
            if line[0] != '*':
                continue
            matchLoc = locRE.match(line)
            if matchLoc:
                CDLevent = True
                if thisCDL:
                    writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
                    thisCDL, thisSAT = None, 0
                tapename = matchLoc.group('name')
                if tapename in IDs:
                    tapename, CDLevent = None, False
                continue
            matchCdl1 = cdl1re.match(line)
            if CDLevent and matchCdl1:
                thisCDL = cdl1Parse(matchCdl1)
                thisSAT = 0
                continue
            matchCdl2 = cdl2re.match(line)
            if CDLevent and matchCdl2:
                thisSAT = float(matchCdl2.group('sat'))
                writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
                tapename, CDLevent, thisCDL, thisSAT = None, False, None, 0
                continue
    if thisCDL:
        writeCDL(CCC, IDs, tapename, thisCDL, thisSAT)
        tapename, CDLevent, thisCDL, thisSAT = None, False, None, 0

    edlInput.close()

    if not CCC:
        print "No Color Decision(s) found in EDL file \"%s\". Quitting." % os.path.split(edlInput.name)[1]
        sys.exit(0)
    print " * %d Color Decision(s) found in EDL file \"%s\"." % (len(CCC), os.path.split(edlInput.name)[1])

    if args.format == 'ccc':
        root = Element('ColorCorrectionCollection', {'xmlns': 'urn:ASC:CDL:v1.01'})

        for cc in CCC:
            appendCCXML(cc['id'], cc['slope'], cc['offset'], cc['power'], cc['SAT'], root)

        with open(output, 'w') as cccOut:
            cccOut.write(prettify(root))

        print " * %d CDL(s) written in CCC file \"%s\"" % (len(CCC), os.path.split(output)[1])
    else:
        for cc in CCC:
            if args.format == 'cdl':
                root = Element('ColorDecisionList', {'xmlns': 'urn:ASC:CDL:v1.01'})
                appendCCXML(cc['id'], cc['slope'], cc['offset'], cc['power'], cc['SAT'], root)
            else:
                root = appendCCXML(cc['id'], cc['slope'], cc['offset'], cc['power'], cc['SAT'], None)

            with open(os.path.join(output, "%s.%s" % (cc['id'], args.format)), 'w') as outputFile:
                outputFile.write(prettify(root))
        print " * %d individual %s(s) written in folder \"%s\"." % (len(CCC), args.format, output)

    return
    useCCC = "CDL"
    if len(argv) == 2 and argv[1].lower() not in ["--cdl", "--cc", "--ccc"]:
        useCCC = "CCC"
        infile = os.path.abspath(argv[1])
        basename = os.path.splitext(os.path.split(infile)[-1])[0]
        outfile = os.path.join(outpath, basename + ".ccc")
    elif len(argv) == 3 and (argv[1].lower() == "--ccc" or argv[2].lower() == "--ccc"):
        useCCC = "CCC"
        if argv[2].lower() == "--ccc":
            infile = os.path.abspath(argv[1])
            outpath = os.path.split(infile)[0]
        else:
            infile = os.path.abspath(argv[2])
            outpath = os.path.split(infile)[0]
        basename = os.path.splitext(os.path.split(infile)[-1])[0]
        outfile = os.path.join(outpath, basename + ".ccc")
    if len(argv) == 3 and ((argv[1].lower() not in ["--cdl", "--cc", "--ccc"]) or (argv[3].lower() not in ["--cdl", "-cc", "--ccc"])):
        useCCC = "CCC"
        infile = os.path.abspath(argv[1])
        basename = os.path.splitext(os.path.split(infile)[-1])[0]
        if os.path.isdir(argv[2]):
            outfile = os.path.join(
                argv[2], os.path.splitext(basename)[0] + ".ccc")
        else:
            outfile = os.path.abspath(argv[2])
    elif len(argv) == 4 and ((argv[3].lower() in ["--cdl", "--cc", "--ccc"]) or (argv[1].lower() in ["--cdl", "--cc", "--ccc"])):
        if argv[3].lower() in ["--cdl", "--cc", "--ccc"]:
            infile = os.path.abspath(argv[1])
            basename = os.path.splitext(os.path.split(infile)[-1])[0]
            if argv[3].lower() == "--ccc":
                useCCC = "CCC"
                if os.path.isdir(argv[2]):
                    outfile = os.path.join(
                        argv[2], os.path.splitext(basename)[0] + ".ccc")
                else:
                    outfile = os.path.abspath(argv[2])
            else:
                if argv[3].lower() == "--cdl":
                    useCCC = "CDL"
                else:
                    useCCC = "CC"
                outpath = os.path.abspath(argv[2])
        else:
            infile = os.path.abspath(argv[2])
            if argv[1].lower() == "--ccc":
                useCCC = "CCC"
                if os.path.isdir(argv[3]):
                    outfile = os.path.join(
                        argv[3], os.path.splitext(basename)[0] + ".ccc")
                else:
                    outfile = os.path.abspath(argv[3])
            else:
                if argv[1].lower() == "--cdl":
                    useCCC = "CDL"
                else:
                    useCCC = "CC"
                outpath = os.path.abspath(argv[3])
    else:
        print " * SYNTAX:  %s  infile.EDL  [outpathname]  [--cdl|cc|ccc]\n" % os.path.split(argv[0])[-1]
        print "            A CMX3600-like EDL file is expected as input and a target folder as"
        print "            output. By default, single CCC (color correction collection, --ccc)"
        print "            file is created, otherwise a target folder is created with a single"
        print "            CDL (--cdl) or CC (--cc) file per every EDL event's color decision."
        print "            Color correction IDs (ccid) are assinged as the EDL event tapenames"
        sys.exit(1)

    camre = re.compile(r"\*\s?FROM\sCLIP\sNAME:\s+.*(?P<name>[A-Z][0-9]{3}[_]?C[0-9]{3})")
    camre0 = re.compile(r"\*\sFROM\sCLIP\sNAME:\s+(?P<name>.{63})")
    camre1 = re.compile(r"[*]\s(?P<name>.*)")
    #Greedier FROM CLIP NAME Regex
    camre3 = re.compile(r"\*\s?FROM\sCLIP\sNAME:\s+(?P<name>[A-Z0-9_\-]+)")
    input_desc, viewing_desc = None, "EDL2CDL script by Walter Arrighetti"
    tapere = re.compile(r"\*\sFROM\sCLIP\sNAME:\s+(?P<name>[A-Za-z0-9-_,.]|\s{8,32})")
    cdl1re = re.compile(r"\*\s?ASC[_]SOP\s+[(]\s?(?P<sR>[-]?\d+[.]\d{4,6})\s+(?P<sG>[-]?\d+[.]\d{4,6})\s+(?P<sB>[-]?\d+[.]\d{4,6})\s?[)]\s?[(]\s?(?P<oR>[-]?\d+[.]\d{4,6})\s+(?P<oG>[-]?\d+[.]\d{4,6})\s+(?P<oB>[-]?\d+[.]\d{4,6})\s?[)]\s?[(]\s?(?P<pR>[-]?\d+[.]\d{4,6})\s+(?P<pG>[-]?\d+[.]\d{4,6})\s+(?P<pB>[-]?\d+[.]\d{4,6})\s?[)]")
    cdl2re = re.compile(r"\*\s?ASC[_]SAT\s+(?P<sat>\d+[.]\d{4,6})")

    ln = 0

    CCC, IDs = [], []


    if (useCCC in ["CDL", "CC"]) and ((not os.path.exists(outpath)) or (not os.path.isdir(outpath))):
        try:
            os.mkdir(outpath)
        except:
            print " * ERROR!: Unable to create output folder \"%s\"." % outpath
            sys.exit(2)
    tapename, CDLevent, thisCDL, thisSAT = None, False, None, 0
    try:
        EDL = open(infile, "rU").readlines()
    except:
        print " * ERROR!: Unable to read input EDL file \"%s\"." % infile
        sys.exit(3)
    for n in range(len(EDL)):
        line = EDL[n].strip()
        if camre.match(line):
            CDLevent, L = True, camre.match(line)
            if thisCDL:
                writeCDL(tapename, thisCDL, thisSAT)
                thisCDL, thisSAT = None, 0
            tapename = L.group("name")
            if tapename in IDs:
                tapename, CDLevent = None, False
        elif camre0.match(line) and n < len(EDL) - 1 and camre1.match(EDL[n + 1]):
            n += 1
            line = line + camre1.match(EDL[n]).group("name")
            L = camre.match(line)
            if not L:
                writeCDL(tapename, thisCDL, thisSAT)
                thisCDL, thisSAT = None, 0
            else:
                CDLevent = True
            tapename = L.group("name")
            if tapename in IDs:
                tapename, CDLevent = None, False
            if thisCDL:
                thisCDL, thisSAT = None, 0
        elif tapere.match(line):
            CDLevent, L = True, tapere.match(line)
            if thisCDL:
                writeCDL(tapename, thisCDL, thisSAT)
                thisCDL, thisSAT = None, 0
            tapename = L.group("name")
            if tapename in IDs:
                tapename, CDLevent = None, False
        elif camre3.match(line):
            CDLevent, L = True, camre3.match(line)
            if thisCDL:
                writeCDL(tapename, thisCDL, thisSAT)
                thisCDL, thisSAT = None, 0
            tapename = L.group("name")
            if tapename in IDs:
                tapename, CDLevent = None, False
        elif CDLevent and cdl1re.match(line):
            L = cdl1re.match(line)
            thisCDL = (tuple(map(float, (L.group("sR"), L.group("sG"), L.group("sB")))), tuple(map(float, (L.group(
                "oR"), L.group("oG"), L.group("oB")))), tuple(map(float, (L.group("pR"), L.group("pG"), L.group("pB")))))
            thisSAT = 0
        elif CDLevent and thisCDL and cdl2re.match(line):
            L = cdl2re.match(line)
            thisSAT = float(L.group("sat"))
            writeCDL(tapename, thisCDL, thisSAT)
            tapename, CDLevent, thisCDL, thisSAT = None, False, None, 0
    if thisCDL:
        writeCDL(tapename, thisCDL, thisSAT)
        tapename, CDLevent, thisCDL, thisSAT = None, False, None, 0
    if not CCC:
        print "No Color Decision(s) found in EDL file \"%s\". Quitting." % os.path.split(infile)[1]
        sys.exit(0)
    print " * %d Color Decision(s) found in EDL file \"%s\"." % (len(CCC), os.path.split(infile)[1])

    if useCCC == "CCC":
        try:
            CCCout = open(outfile, "w")
        except:
            print " * ERROR!: Unable to create output CCC file \"%s\"." % outfile
            sys.exit(3)
        buf = []
        buf.append('<?xml version="1.0" encoding="UTF-8"?>')
        buf.append('<ColorCorrectionCollection xmlns="urn:ASC:CDL:v1.01">')
        if input_desc:
            buf.append('\t<InputDescription>%s</InputDescription>' % input_desc)
        if viewing_desc:
            buf.append('\t<ViewingDescription>%s</ViewingDescription>' %
                       viewing_desc)
        for n in range(len(CCC)):
            buf.append('\t<ColorCorrection id="%s">' % CCC[n]['id'])
            buf.append('\t\t<SOPNode>')
            buf.append('\t\t\t<Slope>%.05f %.05f %.05f</Slope>' % CCC[n]['slope'])
            buf.append('\t\t\t<Offset>%.05f %.05f %.05f</Offset>' %
                       CCC[n]['offset'])
            buf.append('\t\t\t<Power>%.05f %.05f %.05f</Power>' % CCC[n]['power'])
            buf.append('\t\t</SOPNode>')
            buf.append('\t\t<SatNode>')
            buf.append('\t\t\t<Saturation>%.05f</Saturation>' % CCC[n]['SAT'])
            buf.append('\t\t</SatNode>')
            buf.append('\t</ColorCorrection>')
        buf.append('</ColorCorrectionCollection>')
        CCCout.write('\n'.join(buf))
        CCCout.close()
        print " * %d CDL(s) written in CCC file \"%s\"" % (len(CCC), os.path.split(outfile)[1])
    elif useCCC in ["CC", "CDL"]:
        for n in range(len(CCC)):
            outfile = os.path.join(outpath, CCC[n]['id'])
            if useCCC == "CDL":
                outfile += ".cdl"
            else:
                outfile += ".cc"
            try:
                CDLout = open(outfile, "w")
            except:
                print " * ERROR!: Unable to create output CDL file \"%s\"." % outfile
            buf = []
            if useCCC == "CDL":
                buf.append('<?xml version="1.0" encoding="UTF-8"?>')
                buf.append('<ColorDecisionList xmlns="urn:ASC:CDL:v1.01">')
                tab = '\t'
            else:
                tab = ''
            buf.append(tab + '<ColorCorrection id="%s">' % CCC[n]['id'])
            if input_desc:
                buf.append(
                    tab + '\t<InputDescription>%s</InputDescription>' % input_desc)
            if viewing_desc:
                buf.append(
                    tab + '\t<ViewingDescription>%s</ViewingDescription>' % viewing_desc)
            buf.append(tab + '\t<SOPNode>')
            buf.append(tab + '\t\t<Slope>%.05f %.05f %.05f</Slope>' %
                       CCC[n]['slope'])
            buf.append(tab + '\t\t<Offset>%.05f %.05f %.05f</Offset>' %
                       CCC[n]['offset'])
            buf.append(tab + '\t\t<Power>%.05f %.05f %.05f</Power>' %
                       CCC[n]['power'])
            buf.append(tab + '\t</SOPNode>')
            buf.append(tab + '\t<SatNode>')
            buf.append(tab + '\t\t<Saturation>%.05f</Saturation>' % CCC[n]['SAT'])
            buf.append(tab + '\t</SatNode>')
            buf.append(tab + '</ColorCorrection>')
            if useCCC == "CDL":
                buf.append('</ColorDecisionList>')
            CDLout.write('\n'.join(buf))
            CDLout.close()
        print " * %d individual %s(s) written in folder \"%s\"." % (len(CCC), useCCC, outpath)
    else:
        print " * ERROR!: Invalid Color Decision List mode '%s'; quitting." % useCCC
        sys.exit(9)
    sys.exit(0)

if __name__ == "__main__":
    #Pass Along everything but this very script
    main(sys.argv)
