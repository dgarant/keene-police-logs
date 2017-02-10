
python cleardb.py
files=`ls txt | perl -MList::Util=shuffle -e 'print shuffle<STDIN>'`
for f in $files
do
    grep -q $f goodfiles.txt
    if [ $? -eq 0 ]; then
        continue
    fi
    echo "Loading $f"
    python parse_pdf.py txt/$f
    if [ ! $? -eq 0 ]; then
        echo $f >> badfiles.txt
        continue
    fi
    echo $f >> goodfiles.txt
done

