#!/usr/bin/env python3

import textwrap
import random

def main():

    dag_txt = ''

    #
    # submit descriptions
    #
    
    # preproc.sub
    dag_txt += textwrap.dedent('''\
        SUBMIT-DESCRIPTION sweep_init.sub {
                container_image = docker://tdnguyen25/ospool-classification:latest
                universe = container

                executable = ./prelude/sweep_init.py
                arguments = $(config_pathname) $(output_config_pathname)
                log = logs/sweep_init_$(Cluster)_$(Process).log
                error = logs/sweep_init_$(Cluster)_$(Process).err
                output = logs/sweep_init_$(Cluster)_$(Process).out

                should_transfer_files = YES
                when_to_transfer_output = ON_EXIT
                transfer_input_files = $(config_pathname)
                transfer_output_files = $(output_config_pathname)

                request_cpus = 1
                request_memory = 4GB
                request_disk = 4GB
        }


        SUBMIT-DESCRIPTION run_init.sub {
                container_image = docker://tdnguyen25/ospool-classification:latest
                universe = container

                executable = ./run/run_init.py
                arguments = $(config_pathname) $(output_config_pathname)
                log = logs/run_init_$(Cluster)_$(Process).log
                error = logs/run_init_$(Cluster)_$(Process).err
                output = logs/run_init_$(Cluster)_$(Process).out

                should_transfer_files = YES
                when_to_transfer_output = ON_EXIT
                transfer_input_files = $(config_pathname)
                transfer_output_files = $(output_config_pathname)

                request_cpus = 1
                request_memory = 4GB
                request_disk = 4GB
        }


        SUBMIT-DESCRIPTION pproc.sub {
                container_image = docker://tdnguyen25/ospool-classification:latest
                universe = container

                executable = ./run/geldparse.py
                arguments = $(config_pathname) $(geld_pathname) $(output_tensor_pathname)
                log = logs/pproc_$(Cluster)_$(Process).log
                error = logs/pproc_$(Cluster)_$(Process).err
                output = logs/pproc_$(Cluster)_$(Process).out

                should_transfer_files = YES
                when_to_transfer_output = ON_EXIT
                transfer_input_files = $(config_pathname), ../pproc/intermediate/$(geld_pathname)
                transfer_output_files = $(output_tensor_pathname)

                request_cpus = 1
                request_memory = 20GB
                request_disk = 6GB
        }


        SUBMIT-DESCRIPTION model_init.sub {
                container_image = docker://tdnguyen25/ospool-classification:latest
                universe = container

                executable = ./run/model_init.py
                arguments = $(config_pathname) $(output_model_pathname)
                log = logs/model_init_$(Cluster)_$(Process).log
                error = logs/model_init_$(Cluster)_$(Process).err
                output = logs/model_init_$(Cluster)_$(Process).out

                should_transfer_files = YES
                when_to_transfer_output = ON_EXIT
                transfer_input_files = $(config_pathname)
                transfer_output_files = $(output_model_pathname)

                request_cpus = 1
                request_memory = 4GB
                request_disk = 4GB
        }


        SUBMIT-DESCRIPTION train.sub {
                container_image = docker://tdnguyen25/ospool-classification:latest
                universe = container

                executable = ./run/ml/train.py
                arguments = $(config_pathname) $(tensor_pathname) $(model_pathname) $(output_model_pathname)
                log = logs/train_$(Cluster)_$(Process).log
                error = logs/train_$(Cluster)_$(Process).err
                output = logs/train_$(Cluster)_$(Process).out

                should_transfer_files = YES
                when_to_transfer_output = ON_EXIT
                transfer_input_files = $(config_pathname), $(tensor_pathname), $(model_pathname)
                transfer_output_files = $(output_model_pathname)

                requirements = (OpSysMajorVer == 8) || (OpSysMajorVer == 9)
                require_gpus = (DriverVersion >= 11.1)
                request_gpus = 1
                +WantGPULab = true
                +GPUJobLength = "short"

                request_cpus = 1
                request_memory = 15GB
                request_disk = 4GB
        }


        SUBMIT-DESCRIPTION evaluate.sub {
                container_image = docker://tdnguyen25/ospool-classification:latest
                universe = container

                executable = ./run/ml/evaluate.py
                arguments = $(config_pathname) $(tensor_pathname) $(model_pathname) $(epoch)
                log = logs/evaluate_$(Cluster)_$(Process).log
                error = logs/evaluate_$(Cluster)_$(Process).err
                output = logs/evaluate_$(Cluster)_$(Process).out

                should_transfer_files = YES
                when_to_transfer_output = ON_EXIT
                transfer_input_files = $(config_pathname), $(tensor_pathname), $(model_pathname)

                requirements = (OpSysMajorVer == 8) || (OpSysMajorVer == 9)
                require_gpus = (DriverVersion >= 11.1)
                request_gpus = 1
                +WantGPULab = true
                +GPUJobLength = "short"

                request_cpus = 1
                request_memory = 15GB
                request_disk = 4GB
        }


    ''')

    num_shishkabob = 1
    num_epoch = 5
    
    jobs_txt = ''
    vars_txt = ''
    edges_txt = ''

    dag_txt += 'JOB sweep_init sweep_init.sub\n'
    dag_txt += 'VARS sweep_init config_pathname="config.yaml" output_config_pathname="sweep.yaml"\n'

    for i in range(num_shishkabob): # for each shishkabob
        run_prefix = f'run{i}'
        jobs_txt += textwrap.dedent(f'''\
                JOB {run_prefix}-run_init run_init.sub
                JOB {run_prefix}-pproc pproc.sub
                JOB {run_prefix}-model_init model_init.sub\n''')
        vars_txt += textwrap.dedent(f'''\
                VARS {run_prefix}-run_init config_pathname="sweep.yaml" output_config_pathname="{run_prefix}-config.yaml"
                VARS {run_prefix}-pproc config_pathname="{run_prefix}-config.yaml" geld_pathname="ap2002_geld.json" output_tensor_pathname="ap2002.h5"
                VARS {run_prefix}-model_init config_pathname="{run_prefix}-config.yaml" output_model_pathname="{run_prefix}-model_init.pt"\n''')
        edges_txt += f'PARENT sweep_init CHILD {run_prefix}-run_init\n'

        for j in range(num_epoch): # for each epoch
            jobs_txt += textwrap.dedent(f'''\
                    JOB {run_prefix}-train_epoch{j} train.sub
                    JOB {run_prefix}-evaluate_epoch{j} evaluate.sub''')
            vars_txt += textwrap.dedent(f'''\
                    VARS {run_prefix}-train_epoch{j} config_pathname="{run_prefix}-config.yaml" tensor_pathname="ap2002.h5" model_pathname="{run_prefix}-model_init.pt" output_model_pathname="{run_prefix}-model_epoch{j}.pt"
                    VARS {run_prefix}-evaluate_epoch{j} config_pathname="{run_prefix}-config.yaml" tensor_pathname="ap2002.h5" model_pathname="{run_prefix}-model_epoch{j}.pt" epoch="{j}"''')
            edges_txt += textwrap.dedent(f'''\
                    PARENT {run_prefix}-run_init CHILD {run_prefix}-pproc {run_prefix}-model_init
                    PARENT {run_prefix}-pproc {run_prefix}-model_init CHILD {run_prefix}-train_epoch{j}
                    PARENT {run_prefix}-train_epoch{j} CHILD {run_prefix}-evaluate_epoch{j}''')

            if j < num_epoch-1:
                jobs_txt += '\n'
                vars_txt += '\n'
                edges_txt += '\n'

        dag_txt += '\n' + jobs_txt + '\n' + vars_txt + '\n' + edges_txt + '\n'        


    with open('pipeline.dag', 'w') as f:
        f.write(dag_txt)
    print('generated pipeline.dag')


if __name__ == "__main__":
    main()