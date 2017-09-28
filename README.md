# edl2cdl

This tool is for converting color-correction metadata for advanced theatrical/television workflows, as it relates to a conversion tool for the [ASC **C**olor **D**ecision **L**ist](https://en.wikipedia.org/wiki/ASC_CDL) (*CDL*) metadata: the Academy Award® Technological Achievement winning invention by the [American Society of Cinematography](http://www.theasc.com) (ASC) [Science and Technology Committee](http://www.theasc.com/clubhouse/committee_tech.html) for representation and transportation of cinematographic-quality “color *grading*” information ― from on-set to postproduction. More information at the bottom of the present document.

**`edl2cdl`** reads the CDL metadata embedded, as comments, in the editing events of a CMX3600-like [Edit Decision List](https://en.wikipedia.org/wiki/Edit_decision_list) file (EDL). Every CDL is named after and  differentiated by an identifier called “CCCid” that is read after each EDL event's `ClipName` *comment*-field (so be sure to include it as comment in your EDL). The tool then converts the CDL metadata into either one of three XML-based variants of the ASC CDL file formats:
* A single Color Correction Collection file (*CCC*, `.ccc` file extension) containing all the color decisions in the original EDL. This is also the default output format of **`edl2cdl`**.
* A series of Color Decision List files, each containing SOP+saturation metadata for one individual color decision (*CDL*, `.cdl` file extension).
* A series of Color Correction files, each containing SOP+saturation metadata for one individual color decision (*CC*, `.cc` file extension). *This is not really a standard ASC CDL file format, but is effectively what is supported by many software applications with lighter implementations of CDL* (e.g. The Foundry *Nuke* ).

Since the original ClipName name is transformed into a CCCid and the on-set color-correction usually includes just one version/grade per clip shot, no multiple CDLs are extracted from a single ClipName/TapeName.
The only parameter that can be passed is either `--ccc` (*default* if not explicitly defined) or `--cdl` or `--cc` to specify the corresponding output format. Other than that a first mandatory argument is the pathname of the input EDL file. Optionally a foldername or a filename can be specified as argument (the script intelligently parses the output pathname guessing its use according to different output format). Individual EDL/CC files are generated in a separate folder (that keeps the EDL name, without extension, by default); the single CCC file is by default generated in the same folder (and with the same name) of the EDL file.

## Usage

### To Create A Color Correction Collection, a group of CCs in a single file.

`python edl2cdl.py file.edl path/to/file.ccc`

### To Create Individual CC Files

`python edl2cdl.py file.edl path/to/folder --cc`

This will name each CC file after the corresponding Clip Name in the EDL.

### To Create Individual CDL Files
`python edl2cdl.py file.edl path/to/folder --cdl`

## Details on ASC CDL
Each “color decision”, i.e. a so-called “primary” color grading operator mimicking 35mm film color-timing and telecine operations and affecting the whole frame or sequence of frames, is represented by a 10-tuple of floating point values divided in 3+3+3+1 numbers: (*s*R, *s*G, *s*B), (*o*R, *o*G, *o*B), (*p*R, *p*G, *p*B) and *S*.

The *s*'s are "slope" values, the *o*'s are "offset" values, the *p*'s are "power" values (each triplet containing a different value for the raster image's Red-, Green- and Blue-component codevalues); the capital *S* is a "saturation" parameter. The first 9 floats are also called a "*SOP*" after their triplets' initials, and their mapping formula is, invariably for all three RGB channels (where *x* is the input-color codevalue and *y* the output-color's): *y* = (*s*·*x* + *o*)^*p*.

CDL operators are _pseudo_-invertible, as long as the SOP operations (each individually invertible) are applied in reverse orders). Yet CDLs are not "algebraically closed", as neither every primary color-correction can be represented by a CDL, nor every CDL can be inverted by another CDL. So the set of all the CDLs forms a semigroup.

In order to emulate film color-timing/grading operations, SOP values should be applied ‘on top’ of a *scene*-referred image colorimetry preferably encoded using a *“logarithmic”* transfer characteristic or similar tone curve. Examples of digital colour spaces (in the RGB model) with such characteristics are: [ACEScc](http://acescentral.com/t/acescc-vs-acescct/485), ARRI [Log.C](http://www.arri.com/camera/alexa/workflow/working_with_arriraw/dailies/color_spaces/), Kodak [Cineon](https://en.wikipedia.org/wiki/Cineon) Printing Density (CPD), [REDlogFilm](http://www.red.com/learn/red-101/redlogfilm-redgamma), Panasonic [V-Log](http://pro-av.panasonic.net/en/varicam/common/pdf/VARICAM_V-Log_V-Gamut.pdf), Sony [S-Log3](http://www.xdcam-user.com/2014/03/understanding-sonys-slog3-it-isnt-really-noisy/), Film Log.E/Log.D.
Please refer to the ASC CDL [Wikipedia page](https://en.wikipedia.org/wiki/ASC_CDL) for further description and references.
