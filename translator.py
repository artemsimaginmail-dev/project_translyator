_ASM_RUNTIME = """
 ;-------------------------------------------------------------------
 ; Подпрограмма WRITE_INT: вывод знакового 16-битного целого из AX
 ;-------------------------------------------------------------------
 WRITE_INT PROC
     PUSH AX
     PUSH BX
     PUSH CX
     PUSH DX
     MOV BX, 10
     XOR CX, CX
     CMP AX, 0
     JGE WI_DIGITS
     PUSH AX
     MOV AH, 02h
     MOV DL, '-'
     INT 21h
     POP AX
     NEG AX
 WI_DIGITS:
     XOR DX, DX
     DIV BX
     PUSH DX
     INC CX
     OR AX, AX
     JNZ WI_DIGITS
 WI_PRINT:
     POP DX
     ADD DL, '0'
     MOV AH, 02h
     INT 21h
     LOOP WI_PRINT
     MOV AH, 02h
     MOV DL, 13
     INT 21h
     MOV DL, 10
     INT 21h
     POP DX
     POP CX
     POP BX
     POP AX
     RET
 WRITE_INT ENDP
 
 ;-------------------------------------------------------------------
 ; Подпрограмма READ_INT: ввод знакового 16-битного целого, результат в AX
 ;-------------------------------------------------------------------
 READ_INT PROC
     PUSH BX
     PUSH CX
     PUSH DX
     XOR BX, BX
     XOR CX, CX
 RI_LOOP:
     MOV AH, 01h
     INT 21h
     CMP AL, 13
     JE RI_DONE
     CMP AL, '-'
     JNE RI_NOT_MINUS
     MOV CX, 1
     JMP RI_LOOP
 RI_NOT_MINUS:
     CMP AL, '0'
     JB RI_LOOP
     CMP AL, '9'
     JA RI_LOOP
     SUB AL, '0'
     XOR AH, AH
     PUSH AX
     MOV AX, BX
     MOV DX, 10
     MUL DX
     POP DX
     ADD AX, DX
     MOV BX, AX
     JMP RI_LOOP
 RI_DONE:
     MOV AX, BX
     OR CX, CX
     JZ RI_END
     NEG AX
 RI_END:
     POP DX
     POP CX
     POP BX
     RET
 READ_INT ENDP
 """