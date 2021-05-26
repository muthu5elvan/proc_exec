#!/usr/bin/python3

import sys, getopt
import os
import json
import linecache
import re
from pathlib import Path
import subprocess
from subprocess import check_output, CalledProcessError, STDOUT,PIPE
import itertools
import threading
import time
import json2table 
global program_path
program_path= str(Path(__file__).parent.absolute()) 

for f in os.listdir(program_path+os.sep+"output"):
    os.remove(os.path.join(program_path+os.sep+"output", f))

global program_path_variable
program_path_variable="^$^"

global current_path
current_path = os.path.abspath(os.getcwd())

global final_command_output
final_command_output={}

global static_var_pattern
static_var_pattern=r'\^[a-zA-Z0-9\-_]+\^'

global dynamic_var_pattern
dynamic_var_pattern=r'\^[a-zA-Z0-9\-_]+\*\^'

global thread_number
thread_number=5

global outputfile
outputfile=""
global execute_output
execute_output={}

global command_final
command_final=[]

global execute_output_category
execute_output_category=[]

global f_command_steps
f_command_steps=[]

global steps_json
steps_json={}

global thread_process
thread_process=[]

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print ('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

def file_list(file_name):
    # print(file_name)
    file_data = open(file_name, "r")
    var_list = file_data.readlines()
    file_data.close()
    s_var_list =[]
    for var in var_list:
        if var.strip() != "":
            s_var_list.append(var.strip())
    s_var_list = list(dict.fromkeys(s_var_list))
    return s_var_list

def format_json_data():
    global steps_json
    global f_command_steps
    global execute_output_category
    for command_step in steps_json["command_steps"]:
        if type(command_step["command"]) == type(""): #string update
            f_command_steps.append(command_step["command"])
            execute_output_category.append(command_step["process_name"])
        else: #list update
            for command in command_step["command"]:
                f_command_steps.append(command)
                execute_output_category.append(command_step["process_name"])
    return f_command_steps

def store_data_file(out_file,vars):
    # global final_command_format
    html="""<html>
<head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-wEmeIV1mKuiNpC+IOBjI7aAzPcEZeedi5yW5f2yOq55WWLwNGmvvx4Um1vskeMj0" crossorigin="anonymous">
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
    <script>
        $(document).ready(function () {
            
            if (getUrlParameter('Search')!=""){
                $("#myInput").val(getUrlParameter('Search'))     
                var value = $("#myInput").val().toLowerCase();
                $("#myTable tr").filter(function () {
                    $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
                });       
            }
            $("#myInput").on("input", function () {
                var value = $(this).val().toLowerCase();
                $("#myTable tr").filter(function () {
                    $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
                });
            });
        });
        var getUrlParameter = function getUrlParameter(sParam) {
            var sPageURL = window.location.search.substring(1),
                sURLVariables = sPageURL.split('&'),
                sParameterName,
                i;

            for (i = 0; i < sURLVariables.length; i++) {
                sParameterName = sURLVariables[i].split('=');

                if (sParameterName[0] === sParam) {
                    return typeof sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
                }
            }
            return false;
        };
    </script>
    <style>
        th{
            width: 7%;
        }
    </style>
</head>

<body>
    <nav class="navbar navbar-expand-sm navbar-dark fixed-top bg-dark" style="min-height: 1%;">

        <div class="container-fluid ">
            <a class="navbar-brand">Recon Output</a>
            <input class="form-control me-2" id="myInput" type="text" placeholder="Search ..." aria-label="Search">
            <button class="btn btn-outline-success" onclick='window.location.search="?"+jQuery.param({"Search": $("#myInput").val()})'>Reload</button>

        </div>
    </nav>
    <br><br><br>
    <div class="table-responsive">
    """
    html_end="""</div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0/dist/js/bootstrap.bundle.min.js" integrity="sha384-p34f1UUtsS3wqzfto5wAAmdvj+osOnFyQFpp4Ua3gs/ZVWx6oOypYoCJhGGScy+8" crossorigin="anonymous"></script>
    </body>
</html>"""
    table=json2table.convert(vars,build_direction = "LEFT_TO_RIGHT",table_attributes={"id":"myTable","class":"table table-striped table-hover"})
    with open(out_file,"w+") as file_d:
        file_d.writelines(html+table+html_end)

def main(argvs):
    global final_command_output
    global steps_json
    global command_final
    argv=argvs[1:]
    inputfile = ''
    global outputfile
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print ('test.py -i <inputfile> -o <outputfile>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('test.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    print ('Input file is : ', inputfile)
    print ('Output file is : ', outputfile)

    with open(inputfile) as json_file:
        steps_json = json.load(json_file)
        # print(steps_json)

    format_json_data()
    run_commands()

def static_var_replace(command,output_details={},thread_number=0):
    global steps_json
    global static_var_pattern
    static_change_details=[]
    global program_path
    global program_path_variable

    data_var_list=[]
    change_var_list=re.findall(static_var_pattern,command)
    change_var_list = list(dict.fromkeys(change_var_list))
    for variable in change_var_list:
        steps_json["variables"][variable]=(steps_json["variables"][variable]).replace(program_path_variable,program_path)
        data_var_list.append(steps_json["variables"][variable])
        command=command.replace(variable,steps_json["variables"][variable])
    static_var_formated=[]
    for i in range(len(change_var_list)):
        static_var_formated.append([change_var_list[i],data_var_list[i]])
    # run time list
    if len(output_details)==0:
        return [command,[static_var_formated,[]],[],[]]
    else:
        return [command,[static_var_formated,[]],[output_details["store"]["key"],output_details["store"]["variable"],output_details["extract"]["regex"],output_details["santized"]["regex"]],[thread_number]]

def dynamic_var_replace(command_formated,check_list=False):
    global thread_process
    global steps_json
    global dynamic_var_pattern
    global outputfile
    global thread_number

    try:
        if command_formated[3][0] != 0:
            thread_number=command_formated[3][0]
    except:
        pass
    
    dynamic_change_details=[]
    data_var_list=[]
    command_formated_list=[]
    change_var_list=re.findall(dynamic_var_pattern,command_formated[0])
    change_var_list = list(dict.fromkeys(change_var_list))
    for variable in change_var_list:
        variable=variable.replace("*^","^")
        steps_json["variables"][variable]=(steps_json["variables"][variable]).replace(program_path_variable,program_path)
        file_data=file_list(steps_json["variables"][variable])
        data_var_list.append(file_list(steps_json["variables"][variable]))
    data_var_list=list(itertools.product(*data_var_list))
    command_formated_temp=command_formated[0]
    for data in data_var_list:
        command_formated_temp=command_formated[0]
        dynamic_var_data=[]
        
        for i in range(len(change_var_list)):
            command_formated_temp=command_formated_temp.replace(change_var_list[i],data[i])
            dynamic_var_data.append([change_var_list[i],data[i]])
        final_command=[]
        for d in command_formated:
            final_command.append(d)
        final_command[0]=command_formated_temp
        final_command[1][1]=dynamic_var_data
        # command executing here
        if final_command[2] ==[]:
            if check_list:
                print("[*][-] $> "+final_command[0])
                process = threading.Thread( target=just_execute, args= [final_command[0]] )
                process.start()
                thread_process.append(process)
                while threading.active_count() >= thread_number:
                    threads = threading.active_count()
                    print("[!] Thread Process is Full (Current Running Process : " + str(threads) +" )")
                    sys.stdout.write("\x1b[1A");sys.stdout.write('\x1b[2K');time.sleep(1)  
            else:
                print("[*][-] $> "+final_command[0])
                os.system(final_command[0])

        else:
            try:
                store_key_temp=(final_command[2][0]).count("*")
                if store_key_temp ==0:
                    if check_list:
                        print("[*][S] $> "+final_command[0])
                        process = threading.Thread( target= execute_store, args= [final_command[0],steps_json["variables"][final_command[2][0]],final_command[2][1],final_command[2][2],final_command[2][3]] )
                        process.start()
                        thread_process.append(process)
                        while threading.active_count() >= thread_number:
                            threads = threading.active_count()
                            print("[!] Thread Process is Full (Current Running Process : " + str(threads) +" )")
                            sys.stdout.write("\x1b[1A");sys.stdout.write('\x1b[2K');time.sleep(1)
                    else:
                        print("[*][S] $> "+final_command[0])
                        execute_store(final_command[0],final_command[2][0][final_command[2][0]],final_command[2][1],final_command[2][2],final_command[2][3])
                else:
                    raise Exception("Sorry, no numbers below zero")
            except:
                if not((final_command[2][0]).count("^") > 0):
                    execute_store(final_command[0],final_command[2][0],final_command[2][1],final_command[2][2],final_command[2][3])
                for store_key in final_command[1][1]:
                    if store_key[0]== final_command[2][0]:
                        if check_list:
                            print("[*][S] $> "+final_command[0])
                            process = threading.Thread( target= execute_store, args= [final_command[0],store_key[1],final_command[2][1],final_command[2][2],final_command[2][3]] )
                            process.start()
                            thread_process.append(process)
                            while threading.active_count() >= thread_number:
                                threads = threading.active_count()
                                print("[!] Thread Process is Full (Current Running Process : " + str(threads) +" )")
                                sys.stdout.write("\x1b[1A");sys.stdout.write('\x1b[2K');time.sleep(1)
                        else:
                            print("[*][S] $> "+final_command[0])
                            execute_store(final_command[0],store_key[1],final_command[2][1],final_command[2][2],final_command[2][3])

def just_execute(command):
    os.system(command)
    
def run_commands():
    global steps_json
    global thread_process
    for command_details in steps_json["command_steps"]:
        try:
            if type(command_details["command"]) == type([]):
                thread_process=[]
                # print(command_details["command"],type(command_details["command"]))
                for command in command_details["command"]:
                    try:
                        try:
                            command_formated=static_var_replace(command,command_details["output"],command_details["thread"])
                        except:
                            command_formated=static_var_replace(command,command_details["output"])
                        # print(command_formated)
                        dynamic_var_replace(command_formated,check_list=True)
                    except:
                        command_formated=static_var_replace(command)
                        # print(command_formated)
                        dynamic_var_replace(command_formated,check_list=True)
                for process in thread_process:
                    process.join()
            if type(command_details["command"]) == type(""):
                    try:
                        try:
                            command_formated=static_var_replace(command_details["command"],command_details["output"],command_details["thread"])
                        except:
                            command_formated=static_var_replace(command_details["command"],command_details["output"])
                        # print(command_formated)
                        dynamic_var_replace(command_formated)
                    except:
                        command_formated=static_var_replace(command_details["command"])
                        # print(command_formated)
                        dynamic_var_replace(command_formated)
        except Exception as ex:
            print("[?] Error in json file input process name : "+command_details["process_name"],ex)
            sys.exit()


def execute_store(command,key,variable,extract,santized):
    global outputfile
    global final_command_output
    extracted_output=""
    open_subprocess = subprocess.Popen(command,shell=True,  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess_return = open_subprocess.stdout.read().decode("utf-8") +open_subprocess.stderr.read().decode("utf-8")
    print("[!] Exection is Done for $> "+str(command))
    print("[!] Extraction Pattern : "+str(extract))
    data=[]
    try:
        data =re.findall(extract, subprocess_return,flags=re.S)
        if extract == "":
            raise Exception("Extract Regex Empty")
        if data != []:
            extracted_output=extracted_output.join(data)
        else:
            raise Exception("Extract Data Empty")
    except:
        extracted_output=subprocess_return
    extracted_output=re.sub("\n","<br>", extracted_output)
    extracted_quality_data=re.sub(santized,"", extracted_output)
    try:
        final_command_output[key][variable]=extracted_quality_data
    except:
        final_command_output[key]={}
        final_command_output[key][variable]=extracted_quality_data
    store_data_file(outputfile, final_command_output)

if __name__ == "__main__":
    try:
        # print(sys.argv)
        main(sys.argv)
        # main(['main.py', '-i', 't.json', '-o', 'in.html'])
    except FileNotFoundError as ex:
        print("[-] Kindly give proper file path with file name")
        print(""" USAGE python3 final_out.py -i steps.json -o in.html""")
        # print(ex.strerror,ex.args,ex.__traceback__())
    except Exception as ex:
        print(ex)