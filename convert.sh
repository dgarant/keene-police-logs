
for f in `ls pdfs/`
do
    echo $f
    #gs  -q  -dNODISPLAY -dSAFER  -dDELAYBIND  -dWRITESYSTEMDICT \
    #      -dSIMPLE -f ps2ascii.ps pdfs/$f  -dQUIET  -c quit > txt/$f.txt
    pdftotext -raw pdfs/$f txt/$f.txt
done

