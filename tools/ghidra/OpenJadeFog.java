// Export selected native functions without modifying the saved analysis project.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.nio.file.*;
public class OpenJadeFog extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  String[] a=getScriptArgs(); Path out=Paths.get(a[0]);Files.createDirectory(out);
  DecompInterface dec=new DecompInterface();dec.openProgram(currentProgram);
  try {for(int i=1;i<a.length;i++){
   var addr=toAddr(Long.parseUnsignedLong(a[i],16));Function f=getFunctionAt(addr);
   if(f==null){disassemble(addr);f=createFunction(addr,null);}if(f==null)continue;
   var r=dec.decompileFunction(f,60,monitor);
   if(r.decompileCompleted())Files.writeString(out.resolve(a[i]+".c"),r.getDecompiledFunction().getC());
   StringBuilder s=new StringBuilder();var refs=currentProgram.getReferenceManager().getReferencesTo(addr);
   while(refs.hasNext()){var ref=refs.next();s.append(ref).append(" caller=").append(getFunctionContaining(ref.getFromAddress())).append("\n");}
   Files.writeString(out.resolve(a[i]+"-refs.txt"),s.toString());
  }}finally{dec.dispose();}
 }
}
