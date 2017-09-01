from subprocess import check_output

print(check_output(["Rscript wordsToDNA.r " + "HENLO STINKY BOI"], shell=True))