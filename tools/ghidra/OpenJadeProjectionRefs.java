// Find context-field accesses in functions referencing the active render context.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import java.nio.file.*;
import java.util.*;
public class OpenJadeProjectionRefs extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256()))throw new Exception("Hash mismatch");
  Set<Function> fs=new HashSet<>();
  var refs=currentProgram.getReferenceManager().getReferencesTo(toAddr(0x009ec518));
  while(refs.hasNext()){var f=getFunctionContaining(refs.next().getFromAddress());if(f!=null)fs.add(f);}
  StringBuilder out=new StringBuilder();
  for(var f:fs){var it=currentProgram.getListing().getInstructions(f.getBody(),true);while(it.hasNext()){var ins=it.next();boolean hit=false;
   for(int j=0;j<ins.getNumOperands();j++)for(var obj:ins.getOpObjects(j))if(obj instanceof Scalar){long v=((Scalar)obj).getUnsignedValue();if(v==0xac || v==0xc8)hit=true;}
   if(hit){out.append(f.getEntryPoint()+" "+ins.getAddress()+" "+ins+"\n");}
  }}
  Files.writeString(Paths.get(getScriptArgs()[0]),out.toString());
 }
}
