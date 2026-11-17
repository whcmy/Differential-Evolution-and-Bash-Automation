#include "portable.cpp"
double *OShift=nullptr,*M=nullptr,*y=nullptr,*z=nullptr,*x_bound=nullptr;
int ini_flag=0,n_flag=0,func_flag=0,*SS=nullptr;
extern "C" double evaluate(double *x,int fid){double f;cec14_test_func(x,&f,10,1,fid);return f;}
