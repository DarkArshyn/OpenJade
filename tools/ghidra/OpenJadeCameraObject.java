// Inspect camera-object writers and their native callers in a read-only project.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import java.nio.file.*;
public class OpenJadeCameraObject extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  Path out=Paths.get(getScriptArgs()[0]);Files.createDirectory(out);
  var dec=new DecompInterface();dec.openProgram(currentProgram);StringBuilder log=new StringBuilder();
  try {for(long value:new long[]{0x4839e0L,0x483a10L,0x51dfa0L,0x5a6d10L}){
   var at=toAddr(value);var f=getFunctionAt(at);
   if(f==null){disassemble(at);f=createFunction(at,null);}
   log.append(at).append(" function=").append(f).append("\n");
   if(f==null)throw new Exception("Missing function: "+at);
   var r=dec.decompileFunction(f,60,monitor);if(!r.decompileCompleted())throw new Exception("Decompilation failed: "+at);
   Files.writeString(out.resolve(f.getEntryPoint()+".c"),r.getDecompiledFunction().getC());
   var instructions=currentProgram.getListing().getInstructions(f.getBody(),true);
   while(instructions.hasNext()){var ins=instructions.next();log.append(ins.getAddress()).append(" ").append(ins).append("\n");}
  }}finally{dec.dispose();}
  log.append("Wrapper table metadata at 007f60b8: ").append(Integer.toHexString(getInt(toAddr(0x7f60b8L)))).append("\n");
  log.append("Wrapper table pointer at 007f60bc: ").append(Integer.toHexString(getInt(toAddr(0x7f60bcL)))).append("\n");
  Files.writeString(out.resolve("instructions.txt"),log.toString());
 }
}
