#!/bin/bash

#########################################
## E D I T  here your SBATCH resources ##
#########################################
#SBATCH --job-name=opt_config2_opt_config2___a007_b022_2
#SBATCH --ntasks=4 --nodes=1
#SBATCH --mem-per-cpu=30
#SBATCH --time=0:2:00
#SBATCH --gres=scratch:0
#SBATCH --output="C:\Users\AK\Documents\Daskalakis_Gwydion\AC-Forschi\script_maker2000\tests\tests_dir\tmp3jwkr6nd\output\opt_config2\output\opt_config2___a007_b022_2/slurm_%x_18d_03m_24y-12h_45m_20s.out"
##SBATCH --error=%x.%j.out
#########################################
## Start of job shell script           ##
#########################################

#SBATCH --signal=B:USR1@600
#Implementation of backup mechanisms by signal trapping
#Signal USR1 starts the backup function 600s before walltime limit.
backup_function() {
	echo -e "\n### backup function called.\n###Checkpointing ... at $(date)\n"
	mkdir -pv "${SLURM_SUBMIT_DIR}"
	mkdir -pv "${SLURM_OUTPUT_DIR}/backup_results"

	echo "Creating tgz-file '${SLURM_SUBMIT_DIR}/backup_results_${SLURM_JOB_ID}.tgz' ..."
	tar --xform="s%^%backup_results_${SLURM_JOB_ID}/%" -zcvf "${SLURM_OUTPUT_DIR}/backup_results/backup${SLURM_JOB_NAME}18d_03m_24y-12h_45m_20s.tgz" *

	echo -e "\n### backup function finished at $(date)\n"
	trap - USR1
}
trap 'backup_function' USR1

#SBATCH --signal=B:USR2@20
#20 seconds before the end of the job, write a file to the output directory indicating that the job didn't finish
bwalltime_error_function() {
	echo -e "Walltime Error" > "${SLURM_OUTPUT_DIR}/walltime_error.txt"
	
}
trap 'bwalltime_error_function' USR2








echo " "
echo "### Setting up shell environment and defaults for environment vars ..."
echo " "
# Reset all language and locale dependencies (write floats with a dot "."):
unset LANG
export LC_ALL="C"
# Disable all external multi-threading => MPI is in control
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
# Define fallbacks and "sanitize" important environment variables:
export USER="${USER:=$(logname)}"
export SLURM_JOB_ID="${SLURM_JOB_ID:=$(date +%s)}"
export SLURM_SUBMIT_DIR="${SLURM_SUBMIT_DIR:=$(pwd)}"
export SLURM_JOB_NAME="${SLURM_JOB_NAME:=$(basename "$0")}"
export SLURM_JOB_NAME="${SLURM_JOB_NAME//[^a-zA-Z0-9._-]/_}"
export SLURM_JOB_NUM_NODES="${SLURM_JOB_NUM_NODES:=1}"
export SLURM_CPUS_ON_NODE="${SLURM_CPUS_ON_NODE:=1}"
export SLURM_NTASKS="${SLURM_NTASKS:=1}"
# Increase stack limit to 200M per MPI process (10M system default not sufficient):
ulimit -s 200000

echo " "
echo "### Printing basic job infos to stdout ..."
echo " "
echo "START_TIME             = $(date +'%y-%m-%d %H:%M:%S %s')"
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

echo " "
echo "### Loading software module:"
echo " "
module unload chem/orca
module load chem/orca/5.0.2
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

# set important  variables from python

export SLURM_SUBMIT_DIR=C:\Users\AK\Documents\Daskalakis_Gwydion\AC-Forschi\script_maker2000\tests\tests_dir\tmp3jwkr6nd\output\opt_config2\input\opt_config2___a007_b022_2  # from where the input files are copied
export SLURM_OUTPUT_DIR=C:\Users\AK\Documents\Daskalakis_Gwydion\AC-Forschi\script_maker2000\tests\tests_dir\tmp3jwkr6nd\output\opt_config2\output\opt_config2___a007_b022_2 # where the output is written and copied back
export JOBNAME=opt_config2_opt_config2___a007_b022_2             # name of the job
export INPUTFILE=opt_config2___a007_b022_2.inp        # name of the input file
export OUTPUTFILE=C:\Users\AK\Documents\Daskalakis_Gwydion\AC-Forschi\script_maker2000\tests\tests_dir\tmp3jwkr6nd\output\opt_config2\output\opt_config2___a007_b022_2\opt_config2___a007_b022_2.out      # name of the output file
export MARKED_FILES=opt_config2___a007_b022_2.inp   # list of files to be copied back to the output directory
# example to mark multiple files:
# cp /home/usr/dir/{file1,file2,file3,file4} /home/usr/destination/

echo " "
echo "### Copying input files to TMP_WORK_DIR."
echo " "
cp -v "$SLURM_SUBMIT_DIR"/"$MARKED_FILES" "$TMP_WORK_DIR"/

if [ "$INPUTFILE" = "" -o ! -f "$INPUTFILE" ]; then
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

# create output dir
mkdir -vp "${SLURM_OUTPUT_DIR}"

(
	$ORCA_BIN_DIR/orca "$INPUTFILE" >"${OUTPUTFILE}" 2>&1
	orca_exit_code=$?
) &
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
echo "### Removing orca input file ..."
echo " "
rm -rvf "${TMP_WORK_DIR}/${INPUTFILE}"

echo " "
echo "### Copying back tgz-archive of results to SLURM_OUTPUT_DIR ..."
echo " "
mkdir -vp "${SLURM_OUTPUT_DIR}" # if submit dir has been deleted or moved away
echo "Creating result tgz-file '${JOBNAME}.tgz' ..."
tar -zcvf "${JOBNAME}.tgz" -C "${TMP_WORK_DIR}" . # compress entire content of TMP_WORK_DIR

# copy the tgz file to the output directory
cp -v "${JOBNAME}.tgz" "${SLURM_OUTPUT_DIR}"

# extract the tgz file in the output directory
cd "${SLURM_OUTPUT_DIR}"
tar -xzvf "${JOBNAME}.tgz"

echo " "
echo "Remove tgz file from SLURM_OUTPUT_DIR ..."
echo " "
rm -vf "${JOBNAME}.tgz"

echo " "
echo "### Final cleanup: Remove TMP_WORK_DIR ..."
echo " "
cd "${TMP_BASE_DIR}"
rm -rvf "${TMP_WORK_DIR}"
echo "END_TIME               = $(date +'%y-%m-%d %H:%M:%S %s')"

echo " "
echo "### Exiting with exit code..."
echo " "
echo "Orca exit-coode: $orca_exit_code"
exit $orca_exit_code
