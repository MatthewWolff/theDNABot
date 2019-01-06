# DNA to RNA to words
sequence <- commandArgs(TRUE)
sequence <- toupper(gsub("[[:blank:]]", "", sequence)) # trims whitespace
codonTable <- c(rep("A", 4), rep("R", 6), rep("N", 2), rep("D", 2), rep("C", 2), rep("Q", 2), rep("E", 2), rep("G", 4), rep("H", 2), rep("I", 3), rep("L", 6), rep("K", 2), "M", rep("F", 2), rep("P", 4), rep("S", 6), rep("T", 4), "W", rep("Y", 2), rep("V", 4), rep("*", 3))
names(codonTable) <- c("GCU", "GCC", "GCA", "GCG", "CGU", "CGC", "CGA", "CGG", "AGA", "AGG", "AAU", "AAC", "GAU", "GAC", "UGU", "UGC", "CAA", "CAG", "GAA", "GAG", "GGU", "GGC", "GGA", "GGG", "CAU", "CAC", "AUU", "AUC", "AUA", "UUA", "UUG", "CUU", "CUC", "CUA", "CUG", "AAA", "AAG", "AUG", "UUU", "UUC", "CCU", "CCC", "CCA", "CCG", "UCU", "UCC", "UCA", "UCG", "AGU", "AGC", "ACU", "ACC", "ACA", "ACG", "UGG", "UAU", "UAC", "GUU", "GUC", "GUA", "GUG", "UAA", "UGA", "UAG")
sequence <- unlist(strsplit(sequence,""))
sequence[which(sequence == "A")] <- "U"
sequence[which(sequence == "T")] <- "A"
sequence[which(sequence == "G")] <- "X"
sequence[which(sequence == "C")] <- "G"
sequence[which(sequence == "X")] <- "C"
sequence <- paste(sequence,collapse="") 
codons <- substring(sequence,seq(1,nchar(sequence)-2,3),seq(3,nchar(sequence),3));
words <- codonTable[codons]
words[which(is.na(words))] <- ""
cat(paste(words,collapse=""))