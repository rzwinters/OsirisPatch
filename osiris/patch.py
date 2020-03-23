import global_params
from intFlow import ErrorTypes
import os


def append_addition_overflow_check():
    """
    Append addition overflow check to the end of the evm bytecode string
    :return: the start address of the appended addition overflow check
    """
    global evm
    global jump_table
    end_addr = int(len(evm) / 2)
    source_pc = end_addr + 11
    target_address = end_addr + 18
    evm = evm + global_params.ADDITION_OVERFLOW_CHECK.format(target_address)
    jump_table.append([source_pc, 2, target_address])
    return end_addr


def append_multiplication_overflow_check():
    """
    Append multiplication overflow check to the end of the evm bytecode string
    :return: the start address of the appended multiplication overflow check
    """
    # global evm
    # global jump_table
    # end_addr = int(len(evm) / 2)
    # source_pc = end_addr + 0
    # target_address = end_addr + 0
    # evm = evm + global_params.MULTIPLICATION_OVERFLOW_CHECK.format(target_address)
    # jump_table.append([source_pc, 2, target_address])
    # return end_addr


def append_subtraction_underflow_check():
    """
    Append subtraction underflow check to the end of the evm bytecode string
    :return: the start address of the appended subtraction underflow check
    """
    # global evm
    # global jump_table
    # end_addr = int(len(evm) / 2)
    # source_pc = end_addr + 0
    # target_address = end_addr + 0
    # evm = evm + global_params.SUBTRACTION_UNDERFLOW_CHECK.format(target_address)
    # jump_table.append([source_pc, 2, target_address])
    # return end_addr


def append_division_zero_check():
    """
    Append division zero check to the end of the evm bytecode string
    :return: the start address of the appended division zero check
    """
    # global evm
    # global jump_table
    # end_addr = int(len(evm) / 2)
    # source_pc = end_addr + 0
    # target_address = end_addr + 0
    # evm = evm + global_params.DIVISION_ZERO_CHECK.format(target_address)
    # jump_table.append([source_pc, 2, target_address])
    # return end_addr


def append_modulo_zero_check():
    """
    Append modulo zero check to the end of the evm bytecode string
    :return: the start address of the appended modulo zero check
    """
    # global evm
    # global jump_table
    # end_addr = int(len(evm) / 2)
    # source_pc = end_addr + 0
    # target_address = end_addr + 0
    # evm = evm + global_params.MODULO_ZERO_CHECK.format(target_address)
    # jump_table.append([source_pc, 2, target_address])
    # return end_addr


def patch_arithmetic_errors(contract, contract_evm, contract_sol, _arithmetic_errors, _jump_table, _source_map=None):
    """
    Patch arithmetic errors
    :param contract: contract's evm asm file
    :param contract_evm: contract's processed evm bytecode file
    :param contract_sol: contract's raw evm bytecode file
    :param _arithmetic_errors: arithmetic error array generated by previous analysis
    :param _jump_table: jump table generated by previous analysis
    :param _source_map: contract's source map
    """
    global c_name
    global c_name_evm
    global c_name_sol
    global arithmetic_errors
    global source_map
    global jump_table
    global evm

    c_name = contract
    c_name_evm = contract_evm
    c_name_sol = contract_sol
    arithmetic_errors = _arithmetic_errors
    source_map = _source_map
    jump_table = _jump_table
    with open(c_name_evm) as f:
        evm = f.read().strip()

    # Parse arithmetic error array into bugs dictionary
    bugs = {}
    addition_overflow_found = multiplication_overflow_found = subtraction_underflow_found = False
    division_zero_found = modulo_zero_found = False
    for arithmetic_error in arithmetic_errors:
        if arithmetic_error["validated"]:
            if ErrorTypes.ADDOVERFLOW in arithmetic_error["type"]:
                addition_overflow_found = True
                bugs[arithmetic_error["pc"]] = ErrorTypes.ADDOVERFLOW
            # if ErrorTypes.MULOVERFLOW in arithmetic_error["type"]:
            #     multiplication_overflow_found = True
            #     bugs[arithmetic_error["pc"]] = ErrorTypes.MULOVERFLOW
            # if ErrorTypes.UNDERFLOW in arithmetic_error["type"]:
            #     subtraction_underflow_found = True
            #     bugs[arithmetic_error["pc"]] = ErrorTypes.UNDERFLOW
            # if ErrorTypes.DIVISION in arithmetic_error["type"]:
            #     division_zero_found = True
            #     bugs[arithmetic_error["pc"]] = ErrorTypes.DIVISION
            # if ErrorTypes.MODULO in arithmetic_error["type"]:
            #     modulo_zero_found = True
            #     bugs[arithmetic_error["pc"]] = ErrorTypes.MODULO

    # Append arithmetic error checks to the end of the evm bytecode string
    addition_overflow_check_addr = append_addition_overflow_check() if addition_overflow_found else 0
    multiplication_overflow_check_addr = append_multiplication_overflow_check() if multiplication_overflow_found else 0
    subtraction_underflow_check_addr = append_subtraction_underflow_check() if subtraction_underflow_found else 0
    division_zero_check_addr = append_division_zero_check() if division_zero_found else 0
    modulo_zero_check_addr = append_modulo_zero_check() if modulo_zero_found else 0

    # Patch arithmetic error instructions in reverse
    for pc in sorted(bugs.keys(), reverse=True):
        # Update all the starting addresses of arithmetic error checks
        if addition_overflow_found:
            addition_overflow_check_addr = addition_overflow_check_addr + 7
        if multiplication_overflow_found:
            multiplication_overflow_check_addr = multiplication_overflow_check_addr + 7
        if subtraction_underflow_found:
            subtraction_underflow_check_addr = subtraction_underflow_check_addr + 7
        if division_zero_found:
            division_zero_check_addr = division_zero_check_addr + 7
        if modulo_zero_found:
            modulo_zero_check_addr = modulo_zero_check_addr + 7

        # Update all the jump target addresses which is behind the arithmetic error instruction
        for entry in jump_table:
            source_pc = entry[0]
            position = entry[1]
            target_address = entry[2]
            if target_address > pc:
                target_address = target_address + 7
                entry[2] = target_address
                source_pos = source_pc * 2
                position_pos = position * 2
                new_target_address = int(evm[source_pos:source_pos + position_pos], 16) + 7
                if new_target_address >= 2 ** (position * 8):
                    raise OverflowError("New target address is too large")
                evm = (evm[:source_pos] + '{:0{}x}'.format(new_target_address, position_pos)
                       + evm[source_pos + position_pos:])
            if source_pc > pc:
                source_pc = source_pc + 7
                entry[0] = source_pc

        # Patch the arithmetic error instruction
        jump_check_addr = 0
        if bugs[pc] == ErrorTypes.ADDOVERFLOW:
            jump_check_addr = addition_overflow_check_addr
        elif bugs[pc] == ErrorTypes.MULOVERFLOW:
            jump_check_addr = multiplication_overflow_check_addr
        elif bugs[pc] == ErrorTypes.UNDERFLOW:
            jump_check_addr = subtraction_underflow_check_addr
        elif bugs[pc] == ErrorTypes.DIVISION:
            jump_check_addr = division_zero_check_addr
        elif bugs[pc] == ErrorTypes.MODULO:
            jump_check_addr = modulo_zero_check_addr
        patch_pos = pc * 2
        evm = evm[:patch_pos] + global_params.INSTRUCTION_PATCH.format(pc + 7, jump_check_addr) + evm[patch_pos + 2:]
        jump_table.append([pc + 1, 2, pc + 7])
        jump_table.append([pc + 4, 2, jump_check_addr])

    # Output the patched evm bytecode file
    patched_file = os.path.join(global_params.PATCHED_DIR,
                                c_name.replace('.bin.evm.disasm', '.patched.bin').split('/')[-1])
    with open(patched_file, 'w') as of:
        of.write(evm)