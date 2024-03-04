#!/bin/bash

#########################################
## E D I T  here your SBATCH resources ##
#########################################
#SBATCH --job-name __jobname
#SBATCH --ntasks= __ntasks --nodes=1
#SBATCH --mem-per-cpu= __memcore
#SBATCH --time __walltime
#?DISK?
#?EMAIL?
#########################################
## Start of job shell script           ##
#########################################

#SBATCH --signal=B:USR1@600
#Implementation of backup mechanisms by signal trapping
#Signal USR1 starts the backup function 600s before walltime limit.
backup_function () {
	echo -e "\n### backup function called.\n###Checkpointing ... at $(date)\n" 
	mkdir -pv "${SLURM_SUBMIT_DIR}" 
	
	echo "Creating tgz-file '${SLURM_SUBMIT_DIR}/backup_results_${SLURM_JOB_ID}.tgz' ..."	
	tar --xform="s%^%backup_results_${SLURM_JOB_ID}/%" -zcvf "${SLURM_SUBMIT_DIR}/backup_results_${SLURM_JOB_ID}.tgz" *
            
	echo -e "\n### backup function finished at $(date)\n"
	trap - USR1
}
trap 'backup_function' USR1

echo " "
echo "### Setting up shell environment and defaults for environment vars ..."
echo " "
# Reset all language and locale dependencies (write floats with a dot "."):
unset LANG; export LC_ALL="C"
# Disable all external multi-threading => MPI is in control
export MKL_NUM_THREADS=1; export OMP_NUM_THREADS=1
# Define fallbacks and "sanitize" important environment variables:
export USER="${USER:=`logname`}"
export SLURM_JOB_ID="${SLURM_JOB_ID:=`date +%s`}"
export SLURM_SUBMIT_DIR="${SLURM_SUBMIT_DIR:=`pwd`}"
export SLURM_JOB_NAME="${SLURM_JOB_NAME:=`basename "$0"`}"
export SLURM_JOB_NAME="${SLURM_JOB_NAME//[^a-zA-Z0-9._-]/_}"
export SLURM_JOB_NUM_NODES="${SLURM_JOB_NUM_NODES:=1}"
export SLURM_CPUS_ON_NODE="${SLURM_CPUS_ON_NODE:=1}"
export SLURM_NTASKS="${SLURM_NTASKS:=1}"
# Increase stack limit to 200M per MPI process (10M system default not sufficient):
ulimit -s 200000

echo " "
echo "### Printing basic job infos to stdout ..."
echo " "
echo "START_TIME             = `date +'%y-%m-%d %H:%M:%S %s'`"
echo "HOSTNAME               = ${HOSTNAME}"
echo "USER                   = ${USER}"
echo "SLURM_JOB_NAME         = ${SLURM_JOB_NAME}"
echo "SLURM_JOB_ID           = ${SLURM_JOB_ID}"
echo "SLURM_SUBMIT_DIR       = ${SLURM_SUBMIT_DIR}"
echo "SLURM_JOB_NUM_NODES    = ${SLURM_JOB_NUM_NODES}"
echo "SLURM_CPUS_ON_NODE     = ${SLURM_CPUS_ON_NODE}"
echo "SLURM_NTASKS           = ${SLURM_NTASKS}"
echo "SLURM_JOB_NODELIST     = ${SLURM_JOB_NODELIST}"
echo "---------------- ulimit -a -S ----------------"
ulimit -a -S
echo "---------------- ulimit -a -H ----------------"
ulimit -a -H
echo "----------------------------------------------"

echo " "
echo "### Creating TMP_WORK_DIR directory and changing to it ..."
echo " "
# Single-node jobs => use "${SCRATCH}" as base
# Multi-node jobs  => use "$SLURM_SUBMIT_DIR" (assuming that job has been
#                     submitted from within a workspace area)
# NEVER EVER calculate in your home directory.
if test -n "${SCRATCH}" -a -e "${SCRATCH}" -a -d "${SCRATCH}" -a "${SCRATCH}" != "/scratch" -a "${SCRATCH}" != "/tmp" -a "${SCRATCH}" != "/ramdisk"; then
  TMP_BASE_DIR="${SCRATCH:=/tmp/${USER}}"
else
  TMP_BASE_DIR="${TMPDIR:=/tmp/${USER}}"
fi

JOB_WORK_DIR="${SLURM_JOB_NAME}.${SLURM_JOB_ID%%.*}.$(date +%y%m%d_%H%M%S)"
TMP_WORK_DIR="${TMP_BASE_DIR}/${JOB_WORK_DIR}"
echo "TMP_BASE_DIR           = ${TMP_BASE_DIR}"
echo "JOB_WORK_DIR           = ${JOB_WORK_DIR}"
echo "TMP_WORK_DIR           = ${TMP_WORK_DIR}"
mkdir -vp "${TMP_WORK_DIR}"
cd "${TMP_WORK_DIR}"

###
# set the input and output file path
export SLURM_SUBMIT_DIR= __submit_dir
export SLURM_output_DIR= __output_dir



echo " "
echo "### Loading software module:"
echo " "
module unload chem/orca
module load chem/orca/?VERSION?
if test -z "$ORCA_VERSION"; then
  echo "ERROR: Failed to load module 'chem/orca/'."
  exit 101
fi
module list

echo " "
echo "### Display internal Orca environments..."
echo " "
echo "ORCA_BIN_DIR  = ${ORCA_BIN_DIR}"
echo "ORCA_EXA_DIR  = ${ORCA_EXA_DIR}"
echo "ORCA_VERSION  = ${ORCA_VERSION}"
echo ""

echo " "
echo "### Copying input files to TMP_WORK_DIR."
echo " "
cp -v "$SLURM_SUBMIT_DIR"/*       "$TMP_WORK_DIR"/
#Delete output of Slurm on temporary working dir.
rm -v slurm-*.out

INPUTFILE= __input

if [ "$INPUTFILE" = "" -o ! -f "$INPUTFILE" ];then
	echo " "
	echo "### Input file $INPUTFILE not found! Exit!"
	echo " "
fi


echo " "
echo "### Running application ..."
echo " "

# * HOW TO EXECUTE ORCA JOB:
#
#	orca binary must be launched with the full path, i.e. $ORCA_BIN_DIR/orca <input.file>  
#
# * NOTE TO PARALLEL RUN:
#
#	DO NOT run orca via mpirun -whateveroption $ORCA_BIN_DIR/orca, mpiexec -whateveroption $ORCA_BIN_DIR/orca, or srun $ORCA_BIN_DIR/orca. 
#	The calls to mpirun have been hardcoded in orca binary.
#	ORCA takes care of communicating with the OpenMPI interface on its own when needed.
#    				
#	DO NOT FORGET to use the !Pal keyword in the <input.file> to tell ORCA to start multiple processes.
#                     E.g. to start a 8-cores job can realized with the command block in <input.file>
#
#			%pal
#			nprocs 8
#			end
#
(
$ORCA_BIN_DIR/orca "$INPUTFILE" > ${INPUTFILE%.*}.out 2>&1
orca_exit_code=$?
) &
wait
wait
wait
wait
 
echo " "
echo "### Cleaning up files ... removing unnecessary scratch files ..."
echo " "
rm -vf *.tmp.*

sleep 10 # Sleep some time so potential stale nfs handles can disappear
# Remarks:
# * PLEASE remove all not required files in this script.

echo " "
echo "### Copying back tgz-archive of results to SLURM_OUTPUT_DIR ..."
echo " "
mkdir -vp "${SLURM_OUTPUT_DIR}" # if submit dir has been deleted or moved away
echo "Creating result tgz-file '${SLURM_OUTPUT_DIR}/${JOB_WORK_DIR}.tgz' ..."
tar -zcvf "${SLURM_OUTPUT_DIR}/${JOB_WORK_DIR}.tgz" *

cd SLURM_OUTPUT_DIR
tar -xzf "${SLURM_OUTPUT_DIR}/${JOB_WORK_DIR}.tgz"

echo " "
echo "### Final cleanup: Remove TMP_WORK_DIR ..."
echo " "
cd "${TMP_BASE_DIR}"
rm -rvf "${TMP_WORK_DIR}"
echo "END_TIME               = `date +'%y-%m-%d %H:%M:%S %s'`"

echo " "
echo "### Exiting with exit code..."
echo " "
echo "Orca exit-coode: $orca_exit_code"
exit $orca_exit_code