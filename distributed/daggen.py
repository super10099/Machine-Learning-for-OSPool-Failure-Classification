#!/usr/bin/env python3

import textwrap
import random

def main():

    dag_text = ''

    #
    # submit descriptions
    #
    
    # preproc.sub
    dag_text += textwrap.dedent('''\n
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
            container_image = docker://tdnguyen25/pytorch-wandb:latest
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
            container_image = docker://tdnguyen25/pytorch-wandb:latest
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

    variances = [] # hyperparameters
    num_epochs = 10 # number of epochs to train for in each shiskabob
    num_shiskabobs = 10

    # randomly generate variances
    for i in range(num_shiskabobs):
        preproc_hp = {
            'm': random.randint(1, 100),
            'j': random.randint(1, 100), 
            'timeframe_len': random.randint(1, 100)}
        train_hp = {
            'x1': 0,
            'x2': 0,
            'x3': 0}
        variances.append( (preproc_hp, train_hp) )
        

    for i, v in enumerate(variances):
        preproc_hp, train_hp = v
        jobs_text = ''
        vars_text = ''
        # preprocessing of dag
        preproc_hp_string = ''
        for k, val in preproc_hp.items():
            preproc_hp_string += f'{k}="{val}" '
        jobs_text += f'JOB preproc_run{i} preproc.sub\n'
        vars_text += f'VARS preproc_run{i} {preproc_hp_string}\n'

        # training of dag
        train_hp_string = ''
        for k, val in train_hp.items():
            train_hp_string += f'{k}="{val}" '
        for j in range(num_epochs):
            jobs_text += textwrap.dedent(f'''\
                JOB train_run{i}_epoch{j} train.sub
                JOB eval_run{i}_epoch{j} eval.sub\n''')
            vars_text += textwrap.dedent(f'''\
                VARS train_run{i}_epoch{j} {train_hp_string}
                VARS eval_run{i}_epoch{j} model="model_run{i}_epoch{j}.h5"\n''')

        # append the jobs before the vars declarations
        dag_text += jobs_text + vars_text

        # create edges among nodes in current shiskabob
        dag_text += f'PARENT preproc_run{i}_epoch0 CHILD train_run{i}\n'
        for e in range(num_epochs):
            if e < num_epochs - 1: # as last node only has 1 edge, not 2
                dag_text += f'PARENT train_run{i}_epoch{e} CHILD eval_run{i}_epoch{e} train_run{i}_epoch{e + 1}\n'
            else: # last node only has 1 edge, not 2
                dag_text += f'PARENT train_run{i}_epoch{e} CHILD eval_run{i}_epoch{e}\n'
        
        dag_text += '\n'


    with open('pipeline.dag', 'w') as f:
        f.write(dag_text)
    print('generated pipeline.dag')


if __name__ == "__main__":
    main()
